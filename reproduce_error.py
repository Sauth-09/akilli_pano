
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.web.app import app

def reproduce():
    client = app.test_client()
    
    # Login
    login_resp = client.post('/admin/login', data={'password': 'admin'}, follow_redirects=True)
    if b'Giri\xc5\x9f Yap' in login_resp.data: # "Giriş Yap" in response means login failed or redirected back
         # Check if we are already logged in or if password failed
         pass

    # Simulate Save Data
    # Payload similar to what browser sends for class schedules
    data = {
        'action': 'save_settings',
        # General Settings (required to not be overwritten by empty)
        'school_name': 'Test Okul',
        'slideshow_duration': '10',
        
        # Class Schedule Data simulating 50 classes (partial)
        'class_name_0': '9-A',
        'schedule_0_Monday[]': ['Matematik', 'Fizik', 'Kimya', 'Biyoloji', 'Edebiyat', 'Tarih', 'Coğrafya', 'Müzik'],
        'schedule_0_Tuesday[]': ['Beden', 'Beden', 'Matematik', 'Matematik', 'İngilizce', 'İngilizce', 'Din', 'Din'],
    }
    
    # Add dummy data for other fields to prevent errors if they are expected
    data['layout_id[]'] = ['card-status', 'card-duty', 'card-quote', 'card-countdown', 'card-birthdays', 'card-classes']
    data['layout_visible_card-status'] = 'on'
    
    try:
        resp = client.post('/admin', data=data, follow_redirects=True)
        print(f"Response Status: {resp.status_code}")
        if resp.status_code == 500:
            print("Captured 500 Error!")
            # In test client, the exception usually propagates, but since we are running this script, 
            # we might need to catch it if app.testing is True (default False?)
            # Actually Flask test client propagates exceptions by default unless testing=False?
            pass
        else:
            print("Success or other error.")
            # print(resp.data.decode('utf-8'))
            
    except Exception as e:
        print("Caught Exception during request:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure app propagates exceptions for test client
    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    reproduce()
