// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');

    // Initialize the map
    initializeMap();

    // Set up event listeners
    setupEventListeners();
});

function initializeMap() {
    console.log('Initializing map...');
    
    // Check if the map container exists
    var mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }

    try {
        // Initialize the map with a default view
        var map = L.map('map').setView([20, 0], 2);
        console.log('Map initialized:', map);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        console.log('OpenStreetMap tiles added to the map.');

        // Store the map instance globally
        window.balloonMap = map;

        // Initialize marker and flight path variables
        window.launchMarker = null;
        window.flightPath = null;

        // Handle map clicks to set launch location
        map.on('click', function(e) {
            var lat = e.latlng.lat.toFixed(6);
            var lon = e.latlng.lng.toFixed(6);

            console.log('Map clicked at:', lat, lon);

            // Set the launch_latitude and launch_longitude fields
            document.getElementById('launch_latitude').value = lat;
            document.getElementById('launch_longitude').value = lon;

            // If a marker already exists, remove it
            if (window.launchMarker) {
                map.removeLayer(window.launchMarker);
                console.log('Existing launch marker removed.');
            }

            // Add a new marker to the map
            window.launchMarker = L.marker([lat, lon]).addTo(map)
                .bindPopup('Launch Location')
                .openPopup();
            console.log('New launch marker added at:', lat, lon);
        });
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

function setupEventListeners() {
    // Handle Run Simulation button click
    document.getElementById('runSimulation').addEventListener('click', function(event) {
        event.preventDefault();
        console.log('Run Simulation button clicked.');

        // Validate the form
        var form = document.getElementById('predictionForm');
        if (!form.checkValidity()) {
            event.stopPropagation();
            form.classList.add('was-validated');
            console.log('Form validation failed.');
            return;
        }

        // Show loading spinner
        document.getElementById('loading').style.display = 'inline-block';
        console.log('Loading spinner displayed.');

        // Disable the Run Simulation button to prevent multiple clicks
        this.disabled = true;
        console.log('Run Simulation button disabled.');

        // Serialize form data
        var formData = new FormData(form);

        // Send AJAX POST request to /predict
        fetch('/predict', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(handleSimulationResponse)
        .catch(handleSimulationError)
        .finally(() => {
            // Hide loading spinner and enable button regardless of outcome
            document.getElementById('loading').style.display = 'none';
            document.getElementById('runSimulation').disabled = false;
        });
    });
}

function handleSimulationResponse(response) {
    console.log('AJAX request successful. Response:', response);

    // Display simulation results
    document.getElementById('results').innerHTML = `
        <h3>Simulation Results</h3>
        <p><strong>Parachute Deployment Altitude:</strong> ${response.pop_altitude} m</p>
        <p><strong>Parachute Deployment Time:</strong> ${response.pop_time} s</p>
        <p><strong>Landing Time:</strong> ${response.landing_time} s</p>
        <p><strong>Total Simulation Time:</strong> ${response.summary.total_simulation_time} s</p>
        <p><strong>Max Altitude:</strong> ${response.summary.max_altitude} m</p>
        <p><strong>Final Location:</strong> (${response.summary.final_latitude}, ${response.summary.final_longitude})</p>
        <a href="${response.output_files.motion_table_csv}" class="btn btn-success me-2" download>Download Motion Table CSV</a>
        <a href="${response.output_files.flight_trajectory_plot}" class="btn btn-success" download>Download Flight Trajectory Plot</a>
    `;
    document.getElementById('results').style.display = 'block';
    console.log('Simulation results displayed.');

    // Plot flight trajectory on the map
    plotFlightTrajectory(response.prediction, window.balloonMap);
}

function handleSimulationError(error) {
    console.error('AJAX request failed:', error);
    alert('Simulation failed: ' + error.message);
}

function plotFlightTrajectory(trajectory, map) {
    console.log('Plotting flight trajectory...');

    if (!trajectory || trajectory.length === 0) {
        console.error('No trajectory data to plot.');
        return;
    }

    var latlngs = trajectory.map(point => [point.Latitude, point.Longitude]);

    // Remove existing flight path if any
    if (window.flightPath) {
        map.removeLayer(window.flightPath);
    }

    // Add new flight path
    window.flightPath = L.polyline(latlngs, { color: 'red' }).addTo(map);

    // Fit the map view to the flight path
    map.fitBounds(window.flightPath.getBounds());

    // Add markers for launch, deployment, and landing
    addFlightMarkers(trajectory, map);
}

function addFlightMarkers(trajectory, map) {
    // Remove existing markers
    map.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });

    // Launch marker
    var launchPoint = trajectory[0];
    L.marker([launchPoint.Latitude, launchPoint.Longitude], {
        icon: L.icon({ iconUrl: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png' })
    }).addTo(map).bindPopup('Launch Point');

    // Parachute deployment marker
    var deployPoint = trajectory.find(point => point.Parachute_Deployed);
    if (deployPoint) {
        L.marker([deployPoint.Latitude, deployPoint.Longitude], {
            icon: L.icon({ iconUrl: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png' })
        }).addTo(map).bindPopup('Parachute Deployed');
    }

    // Landing marker
    var landingPoint = trajectory[trajectory.length - 1];
    L.marker([landingPoint.Latitude, landingPoint.Longitude], {
        icon: L.icon({ iconUrl: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png' })
    }).addTo(map).bindPopup('Landing Point');
}