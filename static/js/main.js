// static/js/main.js
$(document).ready(function() {
    // Initialize Bootstrap form validation
    (function () {
        'use strict'

        var forms = document.querySelectorAll('.needs-validation')

        Array.prototype.slice.call(forms)
            .forEach(function (form) {
                form.addEventListener('submit', function (event) {
                    if (!form.checkValidity()) {
                        event.preventDefault()
                        event.stopPropagation()
                    }

                    form.classList.add('was-validated')
                }, false)
            })
    })()

    // Initialize Leaflet Map with default view
    var map = L.map('map').setView([0, 0], 2); // Default global view

    // Dark-themed tile layer from CartoDB
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CartoDB',
        maxZoom: 19
    }).addTo(map);

    var polyline; // To store the prediction path

    $('#predictionForm').submit(function(e) {
        e.preventDefault();

        // Check if form is valid
        if (!this.checkValidity()) {
            e.stopPropagation();
            $(this).addClass('was-validated');
            return;
        }

        // Gather form data
        var formData = $(this).serialize(); // Serialize form data

        // Get launch latitude and longitude
        var launch_latitude = parseFloat($('#launch_latitude').val());
        var launch_longitude = parseFloat($('#launch_longitude').val());

        if (isNaN(launch_latitude) || isNaN(launch_longitude)) {
            alert('Invalid launch coordinates.');
            return;
        }

        // Set map view to launch site with animation
        map.flyTo([launch_latitude, launch_longitude], 6, {
            animate: true,
            duration: 2 // Duration in seconds
        });

        // Add a marker for the launch site
        if (window.launchMarker) {
            map.removeLayer(window.launchMarker);
        }
        window.launchMarker = L.marker([launch_latitude, launch_longitude]).addTo(map)
            .bindPopup('Launch Point')
            .openPopup();

        // Show loading spinner
        $('#loading').show();

        // AJAX POST request
        $.ajax({
            url: '/predict',
            type: 'POST',
            data: formData,
            success: function(response) {
                $('#loading').hide();

                if (response.error) {
                    alert('Error: ' + response.error);
                    return;
                }

                // Clear existing polyline and markers if any
                if (polyline) {
                    map.removeLayer(polyline);
                }
                if (window.endMarker) {
                    map.removeLayer(window.endMarker);
                }

                // Process and display prediction
                var coordinates = response.prediction.map(function(point) {
                    return [point.Latitude, point.Longitude];
                });

                if (coordinates.length === 0) {
                    alert('No prediction data available.');
                    return;
                }

                // Add the predicted path to the map
                polyline = L.polyline(coordinates, {color: 'red'}).addTo(map);
                map.fitBounds(polyline.getBounds());

                // Add marker for predicted landing point
                var end = coordinates[coordinates.length - 1];

                if (window.endMarker) {
                    map.removeLayer(window.endMarker);
                }
                window.endMarker = L.marker(end).addTo(map)
                    .bindPopup('Predicted Landing Point');
            },
            error: function(xhr, status, error) {
                $('#loading').hide();
                alert('An error occurred during prediction.');
            }
        });
    });
});
