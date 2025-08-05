#!/usr/bin/env python3
"""Simple test to verify if the quiz buttons respond to clicks"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import sys

def test_quiz_buttons():
    """Test quiz button functionality using browser automation"""
    
    print("🧪 Testing Quiz Button Clicks with Browser Automation")
    print("=" * 60)
    
    # Setup Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        # Try to start Chrome WebDriver
        print("🌐 Starting browser...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to quiz page
        print("📄 Loading quiz page...")
        driver.get("http://127.0.0.1:5000/quiz")
        
        # Wait for page to load
        time.sleep(2)
        
        # Check if page loaded correctly
        title = driver.title
        print(f"📋 Page title: {title}")
        
        # Look for quiz mode cards
        print("🔍 Searching for quiz mode cards...")
        mode_cards = driver.find_elements(By.CLASS_NAME, "mode-card")
        print(f"📊 Found {len(mode_cards)} mode cards")
        
        if len(mode_cards) == 0:
            print("❌ No mode cards found!")
            return False
        
        # Test clicking on each mode card
        modes_tested = []
        for i, card in enumerate(mode_cards):
            try:
                # Get the onclick attribute
                onclick = card.get_attribute("onclick")
                print(f"🎯 Mode card {i+1}: onclick='{onclick}'")
                
                # Click the card
                print(f"🖱️  Clicking mode card {i+1}...")
                driver.execute_script("arguments[0].click();", card)
                
                # Check if it got selected
                classes = card.get_attribute("class")
                if "selected" in classes:
                    print(f"✅ Mode card {i+1} selected successfully")
                    modes_tested.append(f"card_{i+1}")
                else:
                    print(f"❌ Mode card {i+1} not selected after click")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error clicking mode card {i+1}: {str(e)}")
        
        # Test the start quiz button
        print("\n🎯 Testing Start Quiz button...")
        try:
            start_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Start Quiz')]")
            print(f"✅ Found Start Quiz button")
            
            # Click the start button
            print("🖱️  Clicking Start Quiz button...")
            driver.execute_script("arguments[0].click();", start_button)
            
            # Wait for response
            time.sleep(2)
            
            # Check for any changes (quiz container should appear)
            quiz_container = driver.find_elements(By.ID, "quiz-container")
            if quiz_container and quiz_container[0].is_displayed():
                print("✅ Quiz container appeared - Start Quiz working!")
                return True
            else:
                print("❌ Quiz did not start - checking for error messages...")
                
                # Check browser console for errors
                logs = driver.get_log('browser')
                if logs:
                    print("🔍 Browser console errors:")
                    for log in logs:
                        if log['level'] == 'SEVERE':
                            print(f"   ❌ {log['message']}")
                
                return False
                
        except Exception as e:
            print(f"❌ Error with Start Quiz button: {str(e)}")
            return False
        
    except WebDriverException as e:
        print(f"❌ WebDriver error: {str(e)}")
        print("💡 Make sure Chrome is installed and the server is running")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False
    
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    print("Quiz Button Click Test")
    print("Make sure the Flask server is running on http://127.0.0.1:5000")
    print()
    
    try:
        success = test_quiz_buttons()
        
        if success:
            print("\n🎉 Quiz buttons are working correctly!")
        else:
            print("\n⚠️  Quiz buttons have issues that need investigation.")
            print("🔧 Possible solutions:")
            print("   1. Check browser console for JavaScript errors")
            print("   2. Verify CSS is not blocking click events")
            print("   3. Check if mode selection is working properly")
            print("   4. Ensure all JavaScript functions are loaded")
            
    except ImportError:
        print("❌ Selenium not installed. Install with: pip install selenium")
        print("💡 Alternatively, manually test by:")
        print("   1. Open http://127.0.0.1:5000/quiz in browser")
        print("   2. Open browser developer tools (F12)")
        print("   3. Click on mode cards and start button")
        print("   4. Check console for errors")
