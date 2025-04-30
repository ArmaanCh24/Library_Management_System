// Enable Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Book search form
const searchForm = document.querySelector('#book-search-form');
if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
        const searchInput = document.querySelector('input[name="search"]');
        const genreSelect = document.querySelector('select[name="genre"]');
        
        if (!searchInput.value.trim() && !genreSelect.value) {
            e.preventDefault();
            alert('Please enter a search term or select a genre');
        }
    });
}

// Confirm delete actions
document.querySelectorAll('.confirm-delete').forEach(button => {
    button.addEventListener('click', function(e) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });
});

// Dynamic form validation
document.querySelectorAll('input[type="number"]').forEach(input => {
    input.addEventListener('input', function() {
        const value = parseInt(this.value);
        const min = parseInt(this.getAttribute('min') || 0);
        const max = parseInt(this.getAttribute('max') || Infinity);
        
        if (value < min) this.value = min;
        if (value > max) this.value = max;
    });
});
