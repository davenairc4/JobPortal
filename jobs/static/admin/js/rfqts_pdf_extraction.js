// jobs/static/admin/js/rfqts_pdf_extraction.js

document.addEventListener('DOMContentLoaded', function() {
    // Enhance PDF file upload field
    const fileInput = document.querySelector('#id_rfq_file');
    if (fileInput) {
        // Add file size and type validation
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Check file type
                if (file.type !== 'application/pdf') {
                    alert('Please upload a PDF file only.');
                    e.target.value = '';
                    return;
                }
                
                // Check file size (max 10MB)
                const maxSize = 10 * 1024 * 1024; // 10MB
                if (file.size > maxSize) {
                    alert('File size must be less than 10MB.');
                    e.target.value = '';
                    return;
                }
                
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.style.marginTop = '10px';
                fileInfo.style.color = '#666';
                fileInfo.innerHTML = `
                    <strong>Selected file:</strong> ${file.name}<br>
                    <strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB<br>
                    <strong>Type:</strong> ${file.type}
                `;
                
                // Remove any existing file info
                const existingInfo = fileInput.parentElement.querySelector('.file-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                fileInfo.className = 'file-info';
                fileInput.parentElement.appendChild(fileInfo);
            }
        });
    }
    
    // Enhance field mapping selection
    const fieldMappingSelect = document.querySelector('#id_field_mapping');
    if (fieldMappingSelect) {
        // Add help text dynamically
        const helpText = document.createElement('div');
        helpText.className = 'help';
        helpText.style.marginTop = '5px';
        helpText.innerHTML = '<em>Select a field mapping template to customize PDF extraction. Leave empty to use default mapping.</em>';
        fieldMappingSelect.parentElement.appendChild(helpText);
    }
    
    // Highlight changed fields after save
    const messages = document.querySelectorAll('.messagelist .success');
    messages.forEach(message => {
        if (message.textContent.includes('PDF data extracted successfully')) {
            // Highlight fields that were likely changed
            const fieldsToHighlight = [
                'rfqts_no', 'task_title', 'department', 'group', 
                'directorate', 'project_section', 'location'
            ];
            
            fieldsToHighlight.forEach(fieldName => {
                const field = document.querySelector(`#id_${fieldName}`);
                if (field) {
                    field.style.backgroundColor = '#e8f5e9';
                    field.style.border = '2px solid #4caf50';
                    
                    // Add a small indicator
                    const indicator = document.createElement('span');
                    indicator.innerHTML = ' ✓ Extracted from PDF';
                    indicator.style.color = '#4caf50';
                    indicator.style.fontSize = '12px';
                    indicator.style.marginLeft = '10px';
                    
                    const label = field.parentElement.querySelector('label');
                    if (label && !label.querySelector('.pdf-indicator')) {
                        indicator.className = 'pdf-indicator';
                        label.appendChild(indicator);
                    }
                }
            });
        }
    });
    
    // Add confirmation before overwriting existing data
    const saveButton = document.querySelector('input[name="_save"]');
    if (saveButton) {
        saveButton.addEventListener('click', function(e) {
            const fileInput = document.querySelector('#id_rfq_file');
            const hasExistingData = document.querySelector('#id_rfqts_no').value !== 'RFQ-0000';
            
            if (fileInput && fileInput.files.length > 0 && hasExistingData) {
                const confirmed = confirm(
                    'You are uploading a new PDF file. This will attempt to extract and overwrite existing field values. ' +
                    'Do you want to continue?'
                );
                
                if (!confirmed) {
                    e.preventDefault();
                }
            }
        });
    }
    
    // Collapsible sections enhancement
    const collapsibleHeaders = document.querySelectorAll('.collapse h2');
    collapsibleHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const fieldset = this.parentElement;
            fieldset.classList.toggle('collapsed');
        });
    });
});