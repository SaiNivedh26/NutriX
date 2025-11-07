// Theme Toggle
const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    themeToggle.querySelector('.theme-icon').textContent = theme === 'light' ? '🌙' : '☀️';
}

// File Upload
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const imagePreview = document.getElementById('imagePreview');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');

let selectedFile = null;
let macroChart = null;

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--accent)';
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = 'var(--glass-border)';
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--glass-border)';
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    if (!file.type.match('image.*')) {
        alert('Please select an image file');
        return;
    }
    
    selectedFile = file;
    const reader = new FileReader();
    
    reader.onload = (e) => {
        imagePreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
        imagePreview.classList.remove('hidden');
        analyzeBtn.classList.remove('hidden');
        analyzeBtn.disabled = false;
    };
    
    reader.readAsDataURL(file);
}

// Analysis
const loadingPhrases = [
    "🔍 Analyzing your delicious meal...",
    "🥗 Calculating nutritional insights...",
    "📊 Generating personalized nutrition report...",
    "🍽️ Consulting our expert nutrition database...",
    "💡 Uncovering hidden nutritional secrets..."
];

analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    // Hide results, show loading
    resultsSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    analyzeBtn.disabled = true;
    analyzeBtn.querySelector('.btn-text').classList.add('hidden');
    analyzeBtn.querySelector('.btn-loader').classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    const progressFill = document.getElementById('progressFill');
    const loadingText = document.getElementById('loadingText');
    const nutritionText = document.getElementById('nutritionText');
    
    // Clear previous results
    nutritionText.innerHTML = '';
    let fullResponse = '';
    let macros = null;
    let imageBase64 = null;
    
    // Update loading text
    let phraseIndex = 0;
    const phraseInterval = setInterval(() => {
        loadingText.textContent = loadingPhrases[phraseIndex % loadingPhrases.length];
        phraseIndex++;
    }, 1500);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Server error');
        }
        
        // Show results section immediately for streaming
        loadingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        
        // Ensure chart container is visible
        const chartCard = document.querySelector('.chart-card');
        if (chartCard) {
            chartCard.style.display = 'block';
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = ''; // Buffer for incomplete SSE messages
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                // Process any remaining data in buffer
                if (buffer.trim()) {
                    const messages = buffer.split('\n\n');
                    for (const msg of messages) {
                        if (msg.trim() && msg.startsWith('data: ')) {
                            try {
                                const jsonStr = msg.slice(6).trim();
                                if (jsonStr) {
                                    const data = JSON.parse(jsonStr);
                                    if (data.type === 'complete') {
                                        macros = data.macros;
                                        imageBase64 = data.image;
                                        if (macros && macros.carbs !== undefined && macros.proteins !== undefined && macros.fats !== undefined) {
                                            createMacroChart(macros);
                                        }
                                    }
                                }
                            } catch (e) {
                                console.warn('Error parsing final buffer:', e);
                            }
                        }
                    }
                }
                break;
            }
            
            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });
            
            // SSE messages are separated by \n\n
            // Process complete messages (those ending with \n\n)
            while (buffer.includes('\n\n')) {
                const messageEnd = buffer.indexOf('\n\n');
                const message = buffer.substring(0, messageEnd);
                buffer = buffer.substring(messageEnd + 2); // Remove processed message
                
                if (message.trim() === '') continue; // Skip empty messages
                
                // Extract data line from SSE message
                const lines = message.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.slice(6).trim();
                            if (!jsonStr) continue; // Skip empty data lines
                            
                            const data = JSON.parse(jsonStr);
                            
                            if (data.type === 'chunk') {
                                fullResponse += data.chunk;
                                // Highlight numbers in the full response and update display
                                const highlightedResponse = highlightNumbers(fullResponse);
                                nutritionText.innerHTML = highlightedResponse;
                                // Store for sharing
                                currentNutritionText = highlightedResponse;
                                // Auto-scroll to bottom
                                nutritionText.scrollTop = nutritionText.scrollHeight;
                                // Update progress
                                progressFill.style.width = `${Math.min(90, (fullResponse.length / 1000) * 90)}%`;
                            } else if (data.type === 'complete') {
                                macros = data.macros;
                                imageBase64 = data.image;
                                progressFill.style.width = '100%';
                                
                                // Update image preview
                                if (imageBase64) {
                                    imagePreview.innerHTML = `<img src="${imageBase64}" alt="Analyzed Meal">`;
                                }
                                
                                // Store macros for sharing
                                currentMacros = macros;
                                
                                // Create chart after ensuring results section is visible
                                // Use requestAnimationFrame to ensure DOM is ready
                                requestAnimationFrame(() => {
                                    setTimeout(() => {
                                        if (macros && macros.carbs !== undefined && macros.proteins !== undefined && macros.fats !== undefined) {
                                            console.log('Creating chart with macros:', macros);
                                            createMacroChart(macros);
                                        } else {
                                            console.error('Invalid macros data:', macros);
                                            // Create chart with defaults if macros are invalid
                                            createMacroChart({ carbs: 40, proteins: 30, fats: 30 });
                                            currentMacros = { carbs: 40, proteins: 30, fats: 30 };
                                        }
                                    }, 200);
                                });
                            } else if (data.type === 'error') {
                                throw new Error(data.error);
                            }
                        } catch (e) {
                            // Only log if it's not a JSON parse error for incomplete data
                            if (e instanceof SyntaxError && e.message.includes('JSON')) {
                                // This might be an incomplete JSON, skip for now
                                console.warn('Incomplete JSON chunk, buffering...', e.message);
                            } else {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    }
                }
            }
        }
        
        clearInterval(phraseInterval);
        
    } catch (error) {
        clearInterval(phraseInterval);
        alert('Error: ' + error.message);
        console.error('Analysis error:', error);
        loadingSection.classList.add('hidden');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.querySelector('.btn-text').classList.remove('hidden');
        analyzeBtn.querySelector('.btn-loader').classList.add('hidden');
        progressFill.style.width = '0%';
    }
});

function highlightNumbers(text) {
    // Escape HTML first to prevent XSS
    const div = document.createElement('div');
    div.textContent = text;
    let escapedText = div.innerHTML;
    
    // Preserve line breaks
    escapedText = escapedText.replace(/\n/g, '<br>');
    
    // Match numbers (integers and decimals) including percentages
    // More comprehensive pattern to catch all number formats
    const pattern = /(\d+\.?\d*\s*%?)/g;
    return escapedText.replace(pattern, '<span class="number-highlight">$1</span>');
}

function createMacroChart(macros) {
    console.log('createMacroChart called with:', macros);
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded!');
        return;
    }
    
    const chartCanvas = document.getElementById('macroChart');
    if (!chartCanvas) {
        console.error('Chart canvas not found');
        return;
    }
    
    // Ensure results section is visible
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection && resultsSection.classList.contains('hidden')) {
        resultsSection.classList.remove('hidden');
    }
    
    // Ensure canvas is visible
    chartCanvas.style.display = 'block';
    
    // Get container dimensions
    const container = chartCanvas.parentElement;
    let containerWidth = 400;
    if (container) {
        containerWidth = container.offsetWidth || container.clientWidth || 400;
    }
    
    // Get container for proper sizing
    const chartContainer = chartCanvas.parentElement;
    if (chartContainer && chartContainer.classList.contains('chart-container')) {
        // Container will handle sizing via CSS
        chartCanvas.style.width = '100%';
        chartCanvas.style.height = '100%';
    } else {
        chartCanvas.style.width = '100%';
        chartCanvas.style.height = '300px';
    }
    
    const ctx = chartCanvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2d context');
        return;
    }
    
    // Validate macros data
    if (!macros || typeof macros !== 'object') {
        console.error('Invalid macros object:', macros);
        macros = { carbs: 40, proteins: 30, fats: 30 };
    }
    
    // Ensure all values are numbers
    const carbs = typeof macros.carbs === 'number' ? macros.carbs : 40;
    const proteins = typeof macros.proteins === 'number' ? macros.proteins : 30;
    const fats = typeof macros.fats === 'number' ? macros.fats : 30;
    
    console.log('Creating chart with values:', { carbs, proteins, fats });
    
    // Destroy existing chart if it exists
    if (macroChart) {
        try {
            macroChart.destroy();
        } catch (e) {
            console.warn('Error destroying existing chart:', e);
        }
        macroChart = null;
    }
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#ecf0f1' : '#2c3e50';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    try {
        macroChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Carbohydrates', 'Proteins', 'Fats'],
            datasets: [{
                label: 'Percentage (%)',
                data: [carbs, proteins, fats],
                backgroundColor: [
                    'rgba(255, 153, 153, 0.8)',
                    'rgba(102, 178, 255, 0.8)',
                    'rgba(255, 204, 153, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 153, 153, 1)',
                    'rgba(102, 178, 255, 1)',
                    'rgba(255, 204, 153, 1)'
                ],
                borderWidth: 2,
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: isDark ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.9)',
                    titleColor: textColor,
                    bodyColor: textColor,
                    borderColor: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: gridColor
                    }
                },
                x: {
                    ticks: {
                        color: textColor
                    },
                    grid: {
                        color: gridColor
                    }
                }
            }
        }
    });
        console.log('Chart created successfully');
    } catch (error) {
        console.error('Error creating chart:', error);
        console.error('Error details:', error.message, error.stack);
        
        // Try to create a simple fallback chart with defaults
        try {
            if (macroChart) {
                macroChart.destroy();
                macroChart = null;
            }
            // Retry with simpler configuration
            macroChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Carbohydrates', 'Proteins', 'Fats'],
                    datasets: [{
                        label: 'Percentage (%)',
                        data: [carbs, proteins, fats],
                        backgroundColor: ['#ff9999', '#66b2ff', '#ffcc99']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
            console.log('Fallback chart created');
        } catch (fallbackError) {
            console.error('Failed to create fallback chart:', fallbackError);
        }
    }
}

// Update chart theme when theme changes
themeToggle.addEventListener('click', () => {
    setTimeout(() => {
        if (macroChart && selectedFile) {
            const macros = {
                carbs: macroChart.data.datasets[0].data[0],
                proteins: macroChart.data.datasets[0].data[1],
                fats: macroChart.data.datasets[0].data[2]
            };
            createMacroChart(macros);
        }
    }, 100);
});

// Download functionality
const downloadBtn = document.getElementById('downloadBtn');

let currentNutritionText = '';

// Download report as PDF
downloadBtn.addEventListener('click', async () => {
    // Disable button
    downloadBtn.disabled = true;
    const originalText = downloadBtn.querySelector('span').textContent;
    downloadBtn.querySelector('span').textContent = '⏳ Generating PDF...';
    
    try {
        // Get chart image as base64
        const chartCanvas = document.getElementById('macroChart');
        if (!chartCanvas || !macroChart) {
            throw new Error('Chart not available');
        }
        
        const chartImageBase64 = chartCanvas.toDataURL('image/png');
        
        // Get nutrition text (remove HTML highlighting spans but keep text)
        const nutritionDiv = document.getElementById('nutritionText');
        let nutritionText = nutritionDiv ? nutritionDiv.innerText || nutritionDiv.textContent : '';
        
        // If we have stored HTML version, use it and clean it
        if (currentNutritionText) {
            // Remove number highlight spans but keep the numbers
            nutritionText = currentNutritionText.replace(/<span class="number-highlight">/g, '').replace(/<\/span>/g, '');
            nutritionText = nutritionText.replace(/<br>/g, '\n').replace(/<br \/>/g, '\n');
        }
        
        // Send to backend
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chart_image: chartImageBase64,
                nutrition_text: nutritionText
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate PDF');
        }
        
        // Get PDF blob and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `NutriX_Report_${new Date().getTime()}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Show success message briefly
        downloadBtn.querySelector('span').textContent = '✅ Downloaded!';
        setTimeout(() => {
            downloadBtn.querySelector('span').textContent = originalText;
        }, 2000);
        
    } catch (error) {
        alert(`Error generating PDF: ${error.message}`);
        console.error('Download error:', error);
        downloadBtn.querySelector('span').textContent = originalText;
    } finally {
        downloadBtn.disabled = false;
    }
});

// Update stored nutrition text when streaming updates
const observer = new MutationObserver(() => {
    const nutritionDiv = document.getElementById('nutritionText');
    if (nutritionDiv) {
        currentNutritionText = nutritionDiv.innerHTML;
    }
});

// Observe nutrition text changes
setTimeout(() => {
    const nutritionDiv = document.getElementById('nutritionText');
    if (nutritionDiv) {
        observer.observe(nutritionDiv, { childList: true, subtree: true });
    }
}, 1000);

