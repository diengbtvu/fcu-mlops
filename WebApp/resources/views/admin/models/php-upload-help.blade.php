@if(ini_get('upload_max_filesize') && (int)ini_get('upload_max_filesize') < 50)
<div class="alert alert-warning mt-3" role="alert">
    <h6><i class="fas fa-exclamation-triangle"></i> PHP Upload Configuration Notice</h6>
    <p><strong>Current PHP limits are quite low for ML model files:</strong></p>
    <ul class="mb-2">
        <li><code>upload_max_filesize</code>: {{ ini_get('upload_max_filesize') }}</li>
        <li><code>post_max_size</code>: {{ ini_get('post_max_size') }}</li>
        <li><code>max_execution_time</code>: {{ ini_get('max_execution_time') }}s</li>
    </ul>
    
    <p class="mb-2"><strong>For better experience with larger ML models, consider increasing these values in php.ini:</strong></p>
    <pre class="bg-light p-2 small">upload_max_filesize = 100M
post_max_size = 100M
max_execution_time = 300</pre>
    
    <p class="mb-0 small text-muted">
        <strong>Note:</strong> ML models (especially neural networks) can be 10-500MB in size. 
        Current limit of {{ ini_get('upload_max_filesize') }} may prevent uploading real-world models.
    </p>
</div>
@endif
