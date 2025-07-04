// Global variables
let currentUser = null;
let isAdmin = false;
let machines = [];
let bookings = [];

// API Base URL
const API_BASE = 'https://gh-washing-machine.onrender.com/api';

// DOM Elements
const loginModal = document.getElementById('loginModal');
const registerModal = document.getElementById('registerModal');
const adminModal = document.getElementById('adminModal');
const welcomeSection = document.getElementById('welcomeSection');
const userDashboard = document.getElementById('userDashboard');
const adminDashboard = document.getElementById('adminDashboard');

// Google Sign-In Handler
function handleCredentialResponse(response) {
    try {
        // Check if Google Client ID is properly configured
        if (!response || !response.credential) {
            showMessage('Google Sign-In configuration error. Please contact administrator.', 'error');
            return;
        }
        
        // Decode the JWT token to get user info
        const responsePayload = decodeJwtResponse(response.credential);
        
        // Extract email and check if it's LNMIIT domain
        const email = responsePayload.email;
        if (!email.endsWith('@lnmiit.ac.in')) {
            showMessage('Please use your LNMIIT email address', 'error');
            return;
        }
        
        // Extract student ID from email (assuming format: studentid@lnmiit.ac.in)
        const studentId = email.split('@')[0];
        
        // Auto-register or login the user
        googleSignIn(studentId, responsePayload.name, email);
    } catch (error) {
        console.error('Google Sign-In error:', error);
        showMessage('Google Sign-In failed. Please use manual login instead.', 'error');
    }
}

function decodeJwtResponse(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
}

async function googleSignIn(studentId, name, email) {
    try {
        // First try to login
        const loginResponse = await fetch(`${API_BASE}/google-login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_id: studentId,
                email: email,
                name: name
            })
        });

        if (loginResponse.ok) {
            const data = await loginResponse.json();
            currentUser = data.user;
            hideModal(loginModal);
            showUserDashboard();
            showMessage('Google Sign-In successful!', 'success');
        } else {
            // If login fails, try to register
            const registerResponse = await fetch(`${API_BASE}/google-register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    student_id: studentId,
                    username: name,
                    email: email
                })
            });

            if (registerResponse.ok) {
                const data = await registerResponse.json();
                currentUser = data.user;
                hideModal(loginModal);
                showUserDashboard();
                showMessage('Account created and logged in successfully!', 'success');
            } else {
                const errorData = await registerResponse.json();
                showMessage(errorData.message || 'Google Sign-In failed', 'error');
            }
        }
    } catch (error) {
        console.error('Google Sign-In error:', error);
        showMessage('Google Sign-In failed. Please try again.', 'error');
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    checkAuthStatus();
    loadMachines();
});

// Event Listeners
function initializeEventListeners() {
    // Modal controls
    document.getElementById('loginBtn').addEventListener('click', () => showModal(loginModal));
    document.getElementById('adminBtn').addEventListener('click', () => showModal(adminModal));
    document.getElementById('getStartedBtn').addEventListener('click', () => showModal(loginModal));
    document.getElementById('registerLink').addEventListener('click', (e) => {
        e.preventDefault();
        hideModal(loginModal);
        showModal(registerModal);
    });

    // Close modals
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            hideModal(e.target.closest('.modal'));
        });
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            hideModal(e.target);
        }
    });

    // Form submissions
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
    document.getElementById('adminForm').addEventListener('submit', handleAdminLogin);
    document.getElementById('bookingForm').addEventListener('submit', handleBooking);
    document.getElementById('addMachineForm').addEventListener('submit', handleAddMachine);

    // Logout buttons
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('adminLogoutBtn').addEventListener('click', handleLogout);

    // Set minimum datetime for booking
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('startTime').min = now.toISOString().slice(0, 16);
}

// Modal functions
function showModal(modal) {
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function hideModal(modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Authentication functions
async function handleLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const loginData = {
        student_id: formData.get('studentId'),
        password: formData.get('password')
    };

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(loginData)
        });

        const result = await response.json();
        
        if (response.ok) {
            currentUser = result.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            hideModal(loginModal);
            showUserDashboard();
            showMessage('Login successful!', 'success');
        } else {
            showMessage(result.message || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    if (formData.get('password') !== formData.get('confirmPassword')) {
        showMessage('Passwords do not match!', 'error');
        return;
    }

    const registerData = {
        student_id: formData.get('studentId'),
        username: formData.get('username'),
        password: formData.get('password')
    };

    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(registerData)
        });

        const result = await response.json();
        
        if (response.ok) {
            hideModal(registerModal);
            showModal(loginModal);
            showMessage('Registration successful! Please login.', 'success');
        } else {
            showMessage(result.message || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const adminData = {
        admin_id: formData.get('adminId'),
        password: formData.get('adminPassword')
    };

    try {
        const response = await fetch(`${API_BASE}/admin/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(adminData)
        });

        const result = await response.json();
        
        if (response.ok) {
            currentUser = result.admin;
            isAdmin = true;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            localStorage.setItem('isAdmin', 'true');
            hideModal(adminModal);
            showAdminDashboard();
            showMessage('Admin login successful!', 'success');
        } else {
            showMessage(result.message || 'Admin login failed', 'error');
        }
    } catch (error) {
        console.error('Admin login error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

function handleLogout() {
    currentUser = null;
    isAdmin = false;
    localStorage.removeItem('currentUser');
    localStorage.removeItem('isAdmin');
    showWelcomeSection();
    showMessage('Logged out successfully!', 'info');
}

function checkAuthStatus() {
    const savedUser = localStorage.getItem('currentUser');
    const savedIsAdmin = localStorage.getItem('isAdmin');
    
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        isAdmin = savedIsAdmin === 'true';
        
        if (isAdmin) {
            showAdminDashboard();
        } else {
            showUserDashboard();
        }
    }
}

// Dashboard functions
function showWelcomeSection() {
    welcomeSection.style.display = 'block';
    userDashboard.style.display = 'none';
    adminDashboard.style.display = 'none';
}

function showUserDashboard() {
    welcomeSection.style.display = 'none';
    userDashboard.style.display = 'block';
    adminDashboard.style.display = 'none';
    
    document.getElementById('userName').textContent = currentUser.username;
    loadUserBookings();
    populateMachineSelect();
}

function showAdminDashboard() {
    welcomeSection.style.display = 'none';
    userDashboard.style.display = 'none';
    adminDashboard.style.display = 'block';
    
    loadAdminMachines();
    loadAllBookings();
}

// Machine functions
async function loadMachines() {
    try {
        const response = await fetch(`${API_BASE}/machines`);
        const result = await response.json();
        
        if (response.ok) {
            machines = result.machines;
            displayMachines();
        } else {
            console.error('Failed to load machines:', result.message);
        }
    } catch (error) {
        console.error('Error loading machines:', error);
        // Show demo data if API is not available
        machines = [
            { id: 1, machine_name: 'Machine 1', status: 'available' },
            { id: 2, machine_name: 'Machine 2', status: 'in_use' },
            { id: 3, machine_name: 'Machine 3', status: 'available' },
            { id: 4, machine_name: 'Machine 4', status: 'broken' }
        ];
        displayMachines();
    }
}

function displayMachines() {
    const machineList = document.getElementById('machineList');
    if (!machineList) return;

    machineList.innerHTML = '';
    
    // Limit to only 8 machines
    const limitedMachines = machines.slice(0, 8);
    
    limitedMachines.forEach(machine => {
        const machineCard = document.createElement('div');
        machineCard.className = `machine-card ${machine.status}`;
        machineCard.innerHTML = `
            <div class="machine-header">
                <h4>${machine.machine_name}</h4>
                <div class="machine-status status-${machine.status}">
                    ${machine.status.replace('_', ' ').toUpperCase()}
                </div>
            </div>
            <div class="machine-info">
                ${machine.last_used_by ? `<p><i class="fas fa-clock"></i> Last used: ${new Date(machine.last_used_time).toLocaleString()}</p>` : '<p><i class="fas fa-clock"></i> Never used</p>'}
                <button class="btn-info btn-small" onclick="showMachineBookings(${machine.id}, '${machine.machine_name}')">
                    <i class="fas fa-calendar-alt"></i> View Bookings
                </button>
            </div>
        `;
        machineList.appendChild(machineCard);
    });
}

function populateMachineSelect() {
    const machineSelect = document.getElementById('machineSelect');
    if (!machineSelect) return;

    machineSelect.innerHTML = '<option value="">Choose a machine</option>';
    
    // Limit to only 8 machines and filter available ones
    const limitedMachines = machines.slice(0, 8);
    limitedMachines.filter(machine => machine.status === 'available').forEach(machine => {
        const option = document.createElement('option');
        option.value = machine.id;
        option.textContent = machine.machine_name;
        machineSelect.appendChild(option);
    });
}

// Booking functions
async function handleBooking(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const startTime = new Date(formData.get('startTime'));
    const duration = parseFloat(formData.get('duration')); // Use parseFloat to handle 0.5 hours
    const endTime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
    
    const bookingData = {
        machine_id: parseInt(formData.get('machineId')),
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString()
    };

    try {
        const response = await fetch(`${API_BASE}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentUser.id}`
            },
            body: JSON.stringify(bookingData)
        });

        const result = await response.json();
        
        if (response.ok) {
            showMessage('Booking created successfully!', 'success');
            loadUserBookings();
            loadMachines();
            e.target.reset();
        } else {
            showMessage(result.message || 'Booking failed', 'error');
        }
    } catch (error) {
        console.error('Booking error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function loadUserBookings() {
    if (!currentUser) return;

    try {
        const response = await fetch(`${API_BASE}/bookings/user/${currentUser.id}`);
        const result = await response.json();
        
        if (response.ok) {
            displayUserBookings(result.bookings);
        } else {
            console.error('Failed to load bookings:', result.message);
        }
    } catch (error) {
        console.error('Error loading bookings:', error);
        // Show demo data if API is not available
        displayUserBookings([
            {
                id: 1,
                machine_name: 'Machine 1',
                start_time: '2025-06-25T10:00:00',
                end_time: '2025-06-25T12:00:00',
                status: 'confirmed'
            }
        ]);
    }
}

function displayUserBookings(userBookings) {
    const bookingsContainer = document.getElementById('userBookings');
    if (!bookingsContainer) return;

    if (userBookings.length === 0) {
        bookingsContainer.innerHTML = '<p>No bookings found.</p>';
        return;
    }

    bookingsContainer.innerHTML = '';
    
    userBookings.forEach(booking => {
        const bookingCard = document.createElement('div');
        bookingCard.className = 'booking-card';
        bookingCard.innerHTML = `
            <div class="booking-info">
                <div>
                    <strong>${booking.machine_name}</strong>
                </div>
                <div>
                    ${new Date(booking.start_time).toLocaleString()} - 
                    ${new Date(booking.end_time).toLocaleString()}
                </div>
                <div class="booking-status status-${booking.status}">
                    ${booking.status.toUpperCase()}
                </div>
                ${booking.status === 'pending' ? `
                    <button class="btn-danger btn-small" onclick="cancelBooking(${booking.id})">
                        Cancel
                    </button>
                ` : ''}
            </div>
        `;
        bookingsContainer.appendChild(bookingCard);
    });
}

async function cancelBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) return;

    try {
        const response = await fetch(`${API_BASE}/bookings/${bookingId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${currentUser.id}`
            }
        });

        const result = await response.json();
        
        if (response.ok) {
            showMessage('Booking cancelled successfully!', 'success');
            loadUserBookings();
            loadMachines();
        } else {
            showMessage(result.message || 'Failed to cancel booking', 'error');
        }
    } catch (error) {
        console.error('Cancel booking error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

// Admin functions
async function loadAdminMachines() {
    try {
        const response = await fetch(`${API_BASE}/admin/machines`);
        const result = await response.json();
        
        if (response.ok) {
            displayAdminMachines(result.machines);
        } else {
            console.error('Failed to load admin machines:', result.message);
        }
    } catch (error) {
        console.error('Error loading admin machines:', error);
        // Show demo data if API is not available
        displayAdminMachines(machines);
    }
}

function displayAdminMachines(adminMachines) {
    const adminMachineList = document.getElementById('adminMachineList');
    if (!adminMachineList) return;

    adminMachineList.innerHTML = '';
    
    // Limit to only 8 machines for admin portal
    const limitedMachines = adminMachines.slice(0, 8);
    
    limitedMachines.forEach(machine => {
        const machineCard = document.createElement('div');
        machineCard.className = 'admin-machine-card';
        machineCard.innerHTML = `
            <div>
                <h4>${machine.machine_name}</h4>
                <span class="machine-status status-${machine.status}">
                    ${machine.status.replace('_', ' ').toUpperCase()}
                </span>
            </div>
            <div class="machine-controls">
                <button class="btn-success btn-small" onclick="updateMachineStatus(${machine.id}, 'available')">
                    Mark Available
                </button>
                <button class="btn-warning btn-small" onclick="updateMachineStatus(${machine.id}, 'in_use')">
                    Mark In Use
                </button>
                <button class="btn-danger btn-small" onclick="updateMachineStatus(${machine.id}, 'broken')">
                    Mark Broken
                </button>
            </div>
        `;
        adminMachineList.appendChild(machineCard);
    });
}

async function updateMachineStatus(machineId, status) {
    try {
        const response = await fetch(`${API_BASE}/admin/machines/${machineId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentUser.id}`
            },
            body: JSON.stringify({ status })
        });

        const result = await response.json();
        
        if (response.ok) {
            showMessage('Machine status updated successfully!', 'success');
            loadAdminMachines();
            loadMachines();
        } else {
            showMessage(result.message || 'Failed to update machine status', 'error');
        }
    } catch (error) {
        console.error('Update machine status error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleAddMachine(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const machineData = {
        machine_name: formData.get('machineName')
    };

    try {
        const response = await fetch(`${API_BASE}/admin/machines`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentUser.id}`
            },
            body: JSON.stringify(machineData)
        });

        const result = await response.json();
        
        if (response.ok) {
            showMessage('Machine added successfully!', 'success');
            loadAdminMachines();
            loadMachines();
            e.target.reset();
        } else {
            showMessage(result.message || 'Failed to add machine', 'error');
        }
    } catch (error) {
        console.error('Add machine error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function loadAllBookings() {
    try {
        const response = await fetch(`${API_BASE}/admin/bookings`);
        const result = await response.json();
        
        if (response.ok) {
            displayAllBookings(result.bookings);
        } else {
            console.error('Failed to load all bookings:', result.message);
        }
    } catch (error) {
        console.error('Error loading all bookings:', error);
        // Show demo data if API is not available
        displayAllBookings([
            {
                id: 1,
                username: 'John Doe',
                student_id: '20BCS001',
                machine_name: 'Machine 1',
                start_time: '2025-06-25T10:00:00',
                end_time: '2025-06-25T12:00:00',
                status: 'confirmed'
            }
        ]);
    }
}

function displayAllBookings(allBookings) {
    const allBookingsContainer = document.getElementById('allBookings');
    if (!allBookingsContainer) return;

    if (allBookings.length === 0) {
        allBookingsContainer.innerHTML = '<p>No bookings found.</p>';
        return;
    }

    allBookingsContainer.innerHTML = '';
    
    allBookings.forEach(booking => {
        const bookingCard = document.createElement('div');
        bookingCard.className = 'booking-card';
        bookingCard.innerHTML = `
            <div class="booking-info">
                <div>
                    <strong>${booking.username}</strong><br>
                    <small>${booking.student_id}</small>
                </div>
                <div>
                    <strong>${booking.machine_name}</strong>
                </div>
                <div>
                    ${new Date(booking.start_time).toLocaleString()} - 
                    ${new Date(booking.end_time).toLocaleString()}
                </div>
                <div class="booking-status status-${booking.status}">
                    ${booking.status.toUpperCase()}
                </div>
            </div>
        `;
        allBookingsContainer.appendChild(bookingCard);
    });
}

// Utility functions
function showMessage(message, type = 'info') {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());

    // Create new message
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;

    // Insert at the top of the main content
    const main = document.querySelector('.main');
    main.insertBefore(messageDiv, main.firstChild);

    // Auto remove after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

// Refresh data periodically
setInterval(() => {
    if (currentUser) {
        loadMachines();
        if (isAdmin) {
            loadAdminMachines();
            loadAllBookings();
        } else {
            loadUserBookings();
        }
    }
}, 30000); // Refresh every 30 seconds


async function showMachineBookings(machineId, machineName) {
    try {
        const response = await fetch(`${API_BASE}/machines/${machineId}/bookings`);
        const result = await response.json();
        
        if (response.ok) {
            displayMachineBookingsModal(result.machine_name, result.bookings);
        } else {
            showMessage(result.message || 'Failed to load machine bookings', 'error');
        }
    } catch (error) {
        console.error('Error loading machine bookings:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

function displayMachineBookingsModal(machineName, bookings) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('machineBookingsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'machineBookingsModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2 id="machineBookingsTitle">Machine Bookings</h2>
                <div id="machineBookingsList" class="bookings-list">
                    <!-- Bookings will be loaded here -->
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add close functionality
        modal.querySelector('.close').addEventListener('click', () => {
            hideModal(modal);
        });
        
        // Close modal on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal(modal);
            }
        });
    }
    
    // Update content
    document.getElementById('machineBookingsTitle').textContent = `${machineName} - Current Bookings`;
    const bookingsList = document.getElementById('machineBookingsList');
    
    if (bookings.length === 0) {
        bookingsList.innerHTML = '<p class="no-bookings">No current bookings for this machine.</p>';
    } else {
        bookingsList.innerHTML = bookings.map(booking => `
            <div class="booking-item">
                <div class="booking-header">
                    <h4>Booking #${booking.id}</h4>
                    <span class="status-badge ${booking.status}">${booking.status}</span>
                </div>
                <div class="booking-details">
                    <p><i class="fas fa-user"></i> <strong>Student:</strong> ${booking.username} (${booking.student_id})</p>
                    <p><i class="fas fa-clock"></i> <strong>Time:</strong> ${formatDateTime(booking.start_time)} - ${formatDateTime(booking.end_time)}</p>
                    <p><i class="fas fa-calendar"></i> <strong>Booked on:</strong> ${formatDateTime(booking.created_at)}</p>
                </div>
            </div>
        `).join('');
    }
    
    showModal(modal);
}

function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'N/A';
    const date = new Date(dateTimeString);
    return date.toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

