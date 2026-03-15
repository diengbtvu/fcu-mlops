"""
Training Progress Tracker
Quản lý và lưu trữ tiến độ training
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TrainingProgressTracker:
    """Class để theo dõi tiến độ training"""
    
    def __init__(self, progress_dir: str = None):
        if progress_dir is None:
            progress_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'training_progress')
        
        self.progress_dir = progress_dir
        os.makedirs(self.progress_dir, exist_ok=True)
    
    def _get_progress_file(self, session_id: str) -> str:
        """Lấy đường dẫn file progress cho session"""
        return os.path.join(self.progress_dir, f"{session_id}.json")
    
    def start_training(self, session_id: str, total_steps: int = 100) -> None:
        """
        Bắt đầu tracking training
        
        Args:
            session_id: Unique session ID
            total_steps: Tổng số steps (default: 100 cho percentage)
        """
        progress_data = {
            'session_id': session_id,
            'status': 'running',
            'progress': 0,
            'total_steps': total_steps,
            'current_step': 0,
            'message': 'Initializing training...',
            'started_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'error': None,
            'result': None
        }
        
        self._save_progress(session_id, progress_data)
        logger.info(f"Started tracking training session: {session_id}")
    
    def update_progress(
        self,
        session_id: str,
        current_step: int = None,
        progress: float = None,
        message: str = None
    ) -> None:
        """
        Cập nhật tiến độ training
        
        Args:
            session_id: Session ID
            current_step: Bước hiện tại
            progress: Phần trăm hoàn thành (0-100)
            message: Thông báo hiện tại
        """
        progress_data = self.get_progress(session_id)
        
        if progress_data is None:
            logger.warning(f"Session {session_id} not found, creating new session")
            self.start_training(session_id)
            progress_data = self.get_progress(session_id)
        
        if current_step is not None:
            progress_data['current_step'] = current_step
            progress_data['progress'] = (current_step / progress_data['total_steps']) * 100
        
        if progress is not None:
            progress_data['progress'] = min(progress, 100)
        
        if message is not None:
            progress_data['message'] = message
        
        progress_data['updated_at'] = datetime.now().isoformat()
        
        self._save_progress(session_id, progress_data)
        logger.debug(f"Updated progress for {session_id}: {progress_data['progress']:.1f}%")
    
    def complete_training(
        self,
        session_id: str,
        result: Dict = None,
        message: str = "Training completed successfully"
    ) -> None:
        """
        Đánh dấu training hoàn thành
        
        Args:
            session_id: Session ID
            result: Kết quả training (metrics, model info, etc.)
            message: Thông báo hoàn thành
        """
        progress_data = self.get_progress(session_id)
        
        if progress_data:
            progress_data['status'] = 'completed'
            progress_data['progress'] = 100
            progress_data['message'] = message
            progress_data['result'] = result
            progress_data['completed_at'] = datetime.now().isoformat()
            progress_data['updated_at'] = datetime.now().isoformat()
            
            self._save_progress(session_id, progress_data)
            logger.info(f"Training completed for session: {session_id}")
    
    def fail_training(
        self,
        session_id: str,
        error: str,
        message: str = "Training failed"
    ) -> None:
        """
        Đánh dấu training thất bại
        
        Args:
            session_id: Session ID
            error: Error message
            message: Thông báo lỗi
        """
        progress_data = self.get_progress(session_id)
        
        if progress_data:
            progress_data['status'] = 'failed'
            progress_data['message'] = message
            progress_data['error'] = error
            progress_data['failed_at'] = datetime.now().isoformat()
            progress_data['updated_at'] = datetime.now().isoformat()
            
            self._save_progress(session_id, progress_data)
            logger.error(f"Training failed for session {session_id}: {error}")
    
    def get_progress(self, session_id: str) -> Optional[Dict]:
        """
        Lấy thông tin tiến độ hiện tại
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict chứa thông tin progress hoặc None
        """
        progress_file = self._get_progress_file(session_id)
        
        if not os.path.exists(progress_file):
            return None
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading progress file: {e}")
            return None
    
    def cleanup_session(self, session_id: str) -> None:
        """
        Xóa file progress sau khi hoàn thành
        
        Args:
            session_id: Session ID
        """
        progress_file = self._get_progress_file(session_id)
        
        if os.path.exists(progress_file):
            try:
                os.remove(progress_file)
                logger.info(f"Cleaned up progress file for session: {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up progress file: {e}")
    
    def _save_progress(self, session_id: str, progress_data: Dict) -> None:
        """Lưu progress data vào file"""
        progress_file = self._get_progress_file(session_id)
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving progress file: {e}")
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """
        Xóa các session cũ
        
        Args:
            hours: Xóa sessions cũ hơn số giờ này
            
        Returns:
            Số lượng sessions đã xóa
        """
        if not os.path.exists(self.progress_dir):
            return 0
        
        deleted_count = 0
        current_time = datetime.now()
        
        for filename in os.listdir(self.progress_dir):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(self.progress_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if (current_time - file_time).total_seconds() > hours * 3600:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting old session file {filename}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old training sessions")
        return deleted_count
