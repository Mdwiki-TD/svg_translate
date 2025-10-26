document.addEventListener('DOMContentLoaded', () => {
    // Get the dark mode toggle button
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (!darkModeToggle) {
        console.warn('Dark mode toggle button not found');
        return;
    }
    const html = document.documentElement;

    // Check for saved theme preference or default to 'light'
    const currentTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-bs-theme', currentTheme);

    // Update the navbar theme
    const navbar = document.querySelector('nav.navbar');
    if (navbar) {
        navbar.setAttribute('data-bs-theme', currentTheme);
    }
    // Update the button icon based on current theme
    updateDarkModeIcon(currentTheme);

    // Add click event listener to the toggle button
    darkModeToggle.addEventListener('click', () => {
        // Get the current theme
        const theme = html.getAttribute('data-bs-theme');

        // Toggle between light and dark
        const newTheme = theme === 'light' ? 'dark' : 'light';

        // Update the html attribute
        html.setAttribute('data-bs-theme', newTheme);
        if (navbar) {
            navbar.setAttribute('data-bs-theme', newTheme);
        }
        // Save the preference in localStorage
        localStorage.setItem('theme', newTheme);

        // Update the button icon
        updateDarkModeIcon(newTheme);
    });

    // Function to update the dark mode icon
    function updateDarkModeIcon(theme) {
        const icon = darkModeToggle.querySelector('i');
        if (!icon) {
            console.warn('Dark mode icon element not found');
            return;
        }
        if (theme === 'dark') {
            icon.className = 'bi bi-sun-fill';
        } else {
            icon.className = 'bi bi-moon-stars-fill';
        }
    }
});
