import requests
from bs4 import BeautifulSoup

def download_attachment_from_aspnet(url):
    # Create a session to maintain cookies (important for ASP.NET)
    session = requests.Session()
    
    # Step 1: GET the page to extract ASP.NET hidden fields
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract ASP.NET hidden fields
    viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
    viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
    
    # Step 2: Prepare the POST data
    post_data = {
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstate_generator,
        '__EVENTTARGET': 'buttonGenerateScript',
        '__EVENTARGUMENT': '',
    }
    
    # Step 3: Send the POST request
    response = session.post(url, data=post_data)
    
    # Step 4: Check if we got the attachment
    if 'attachment' in response.headers.get('Content-Disposition', ''):
        content_disposition = response.headers.get('Content-Disposition', '')

        # Extract filename from Content-Disposition header
        filename = 'script.sql'
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
            
        # Save the file
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        print(f"Downloaded: {filename}")
        return filename
    else:
        print("No attachment found in response")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        return None

# Usage
url = "http://localhost/SP/applogin.aspx"
download_attachment_from_aspnet(url)