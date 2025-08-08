#!/usr/bin/env python3
"""
Test JavaScript execution by creating a simple test HTML page.
"""

html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Achievement Reset Test</title>
</head>
<body>
    <h1>Testing Achievement Reset State</h1>
    
    <div>
        <h3 id="rarest-achievement">None yet - start your journey!</h3>
        <p id="rarest-achievement-label">Getting Started</p>
    </div>
    
    <button onclick="testResetState()">Test Reset State</button>
    <button onclick="testActiveState()">Test Active State</button>
    
    <script>
    // Mock stats data for reset state
    const resetStats = {
        unlocked: 0,
        points: 0,
        completion: 0,
        questions_answered: 0,
        days_studied: 0,
        badges: []
    };
    
    // Mock stats data for active state
    const activeStats = {
        unlocked: 5,
        points: 150,
        completion: 11,
        questions_answered: 25,
        days_studied: 3,
        badges: ['first_steps'],
        rarest: 'Linux Master'
    };
    
    function updateAchievementStats(stats) {
        // Check if this is a reset state (all stats are 0)
        const isResetState = (
            (stats?.unlocked || 0) === 0 &&
            (stats?.points || 0) === 0 &&
            (stats?.completion || 0) === 0 &&
            (stats?.questions_answered || 0) === 0 &&
            (stats?.days_studied || 0) === 0 &&
            (!stats?.badges || stats.badges.length === 0)
        );
        
        if (isResetState) {
            // Show fresh start values for reset state
            document.getElementById('rarest-achievement').textContent = 'None yet - start your journey!';
            
            // Update the label text for reset state
            const rarestLabel = document.getElementById('rarest-achievement-label');
            if (rarestLabel) {
                rarestLabel.textContent = 'Getting Started';
            }
            
            console.log('Applied reset state styling');
        } else {
            // Show actual progress
            document.getElementById('rarest-achievement').textContent = stats?.rarest || 'None';
            
            // Update the label text for active state
            const rarestLabel = document.getElementById('rarest-achievement-label');
            if (rarestLabel) {
                rarestLabel.textContent = 'Rarest Achievement';
            }
            
            console.log('Applied active state styling');
        }
    }
    
    function testResetState() {
        console.log('Testing reset state...');
        updateAchievementStats(resetStats);
    }
    
    function testActiveState() {
        console.log('Testing active state...');
        updateAchievementStats(activeStats);
    }
    
    // Test reset state on load
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Page loaded, testing reset state...');
        testResetState();
    });
    </script>
</body>
</html>
'''

# Write test file
with open('test_achievement_reset.html', 'w') as f:
    f.write(html_content)

print("✅ Created test_achievement_reset.html")
print("📝 This file tests the achievement reset state logic")
print("🌐 You can open it in a browser to verify the JavaScript works correctly")
print("💡 It should show:")
print("   - 'None yet - start your journey!' as the main text")
print("   - 'Getting Started' as the label")
print("   - Buttons to test both reset and active states")
