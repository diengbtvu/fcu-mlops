from flask import Blueprint, request, jsonify
import uuid
from app.utils.progress_tracker import TrainingProgressTracker

progress_bp = Blueprint('progress', __name__, url_prefix='/progress')

# Global progress tracker instance
progress_tracker = TrainingProgressTracker()


@progress_bp.route('/<session_id>', methods=['GET'])
def get_training_progress(session_id):
    """
    API để lấy tiến độ training
    
    GET /progress/<session_id>
    
    Returns:
        {
            "success": true,
            "progress": {
                "session_id": "uuid",
                "status": "running|completed|failed",
                "progress": 0-100,
                "message": "Current status message",
                "started_at": "ISO datetime",
                "updated_at": "ISO datetime",
                "result": {...} // Nếu completed
                "error": "..." // Nếu failed
            }
        }
    """
    progress_data = progress_tracker.get_progress(session_id)
    
    if progress_data is None:
        return jsonify({
            'success': False,
            'error': f'Session {session_id} not found'
        }), 404
    
    return jsonify({
        'success': True,
        'progress': progress_data
    }), 200


@progress_bp.route('/cleanup', methods=['POST'])
def cleanup_old_sessions():
    """
    API để xóa các session cũ
    
    POST /progress/cleanup
    Body: {"hours": 24}
    """
    data = request.get_json() or {}
    hours = data.get('hours', 24)
    
    deleted_count = progress_tracker.cleanup_old_sessions(hours)
    
    return jsonify({
        'success': True,
        'message': f'Cleaned up {deleted_count} old sessions',
        'deleted_count': deleted_count
    }), 200


@progress_bp.route('/generate-session', methods=['POST'])
def generate_session():
    """
    Tạo session ID mới cho training
    
    POST /progress/generate-session
    
    Returns:
        {
            "success": true,
            "session_id": "uuid"
        }
    """
    session_id = str(uuid.uuid4())
    
    return jsonify({
        'success': True,
        'session_id': session_id
    }), 200
