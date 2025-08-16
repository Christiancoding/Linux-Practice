#!/usr/bin/env python3
"""Manual debugging steps for quiz buttons"""

print("""
🔧 MANUAL DEBUGGING STEPS FOR QUIZ BUTTONS
=========================================

Since the API endpoints are working correctly, the issue is in the frontend.
Here's how to debug manually:

1. 🌐 OPEN BROWSER AND NAVIGATE TO QUIZ
   - Open http://127.0.0.1:5000/quiz in your browser
   - Open Developer Tools (F12)
   - Go to the Console tab

2. 🖱️  TEST MODE SELECTION
   - Click on each mode card (Standard, Timed, Survival, Exam)
   - Check if the card gets a 'selected' class added
   - In console, check if you see: "selectMode called with: [mode_name]"
   
3. 🎯 TEST START QUIZ BUTTON
   - Select a mode first (click a mode card)
   - Click "Start Quiz" button
   - Check console for any error messages
   - Look for network requests in Network tab
   
4. 🔍 COMMON ISSUES TO CHECK:
   - JavaScript errors in console (red text)
   - Network errors (failed API calls)
   - CSS z-index issues (elements blocking clicks)
   - Missing event handlers
   
5. 🧪 CONSOLE TESTS YOU CAN RUN:
   
   In browser console, try these commands:
   
   // Test if selectMode function exists
   typeof selectMode
   
   // Test calling selectMode directly
   selectMode('standard')
   
   // Check if quiz state is defined
   typeof quizState
   
   // Test calling startQuiz directly
   startQuiz()
   
   // Check for mode cards
   document.querySelectorAll('.mode-card').length
   
   // Check for start button
   document.querySelector('button[onclick="startQuiz()"]')

6. 🎨 CSS ISSUES TO CHECK:
   
   In Elements tab, verify:
   - Mode cards have onclick attributes
   - Start button has onclick attribute
   - No CSS pointer-events: none
   - No overlapping elements blocking clicks

7. 📊 EXPECTED BEHAVIOR:
   - Clicking mode card should add 'selected' class
   - Console should show "Starting quiz..." when start clicked
   - Page should transition from quiz-setup to quiz-container
   - Network tab should show POST request to /api/start_[mode]

8. 🚨 IF BUTTONS STILL DON'T WORK:
   
   The issue might be:
   - Missing CSS classes for form elements
   - JavaScript event conflicts
   - Template rendering issues
   - Browser caching old JavaScript
   
   Try:
   - Hard refresh (Ctrl+Shift+R)
   - Disable browser cache
   - Check for missing CSS files
   - Verify all JavaScript is loaded

🔧 QUICK FIXES TO TRY:
===================

If you find JavaScript errors, here are common fixes:

1. If "selectMode is not defined":
   - JavaScript didn't load properly
   - Check <script> tags in HTML
   
2. If "Cannot read property of undefined":
   - Missing DOM elements
   - Check element IDs match JavaScript

3. If mode selection doesn't work:
   - Check onclick attributes on mode cards
   - Verify CSS doesn't block clicks

4. If API calls fail:
   - Check Flask server is running
   - Verify API endpoints exist
   - Check CORS settings

Let me know what errors you see in the console!
""")

# Also create a simple HTML test page to isolate the issue
with open('simple_quiz_test.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Simple Quiz Test</title>
    <style>
        .mode-card { 
            border: 1px solid #ccc; 
            padding: 20px; 
            margin: 10px; 
            cursor: pointer; 
            background: white;
        }
        .mode-card.selected { 
            background: lightblue; 
            border-color: blue; 
        }
        button { 
            padding: 10px 20px; 
            font-size: 16px; 
            cursor: pointer; 
        }
        #result { 
            margin: 20px; 
            padding: 10px; 
            border: 1px solid #ddd; 
            background: #f9f9f9; 
        }
    </style>
</head>
<body>
    <h1>Simple Quiz Button Test</h1>
    
    <div class="mode-card" onclick="selectMode('standard')">
        <h3>Standard Mode</h3>
        <p>Click to select</p>
    </div>
    
    <div class="mode-card" onclick="selectMode('timed')">
        <h3>Timed Mode</h3>
        <p>Click to select</p>
    </div>
    
    <select id="quiz-category">
        <option value="All Categories">All Categories</option>
    </select>
    
    <select id="num-questions">
        <option value="20">20 Questions</option>
    </select>
    
    <button onclick="startQuiz()">Start Quiz</button>
    
    <div id="result">Ready to test...</div>
    
    <script>
        let quizState = { mode: null };
        
        function selectMode(mode) {
            console.log('selectMode called with:', mode);
            
            // Clear previous selections
            document.querySelectorAll('.mode-card').forEach(card => {
                card.classList.remove('selected');
            });
            
            // Select current mode
            event.target.closest('.mode-card').classList.add('selected');
            quizState.mode = mode;
            
            document.getElementById('result').innerHTML = 'Selected mode: ' + mode;
        }
        
        function startQuiz() {
            console.log('startQuiz called');
            
            if (!quizState.mode) {
                alert('Please select a mode first');
                return;
            }
            
            const category = document.getElementById('quiz-category').value;
            const numQuestions = document.getElementById('num-questions').value;
            
            const data = {
                mode: quizState.mode,
                category: category,
                num_questions: parseInt(numQuestions)
            };
            
            document.getElementById('result').innerHTML = 'Would start quiz with: ' + JSON.stringify(data);
            console.log('Quiz data:', data);
        }
    </script>
</body>
</html>''')

print("Created simple_quiz_test.html for isolated testing")
print("Open file:///home/retiredfan/Documents/github/linux_plus_study_v3_main/linux_plus_study_v3/simple_quiz_test.html in browser")
