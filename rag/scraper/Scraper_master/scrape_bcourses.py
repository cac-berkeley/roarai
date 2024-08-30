from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import subprocess
import requests
import re
import os
from rag.scraper.Scraper_master.base_scraper import BaseScraper
from utils import save_to_file, create_and_enter_dir, delete_and_exit_dir

class ScrapebCourses(BaseScraper):
    def __init__(self, url, root_folder, calnet_id, passphrase):
        super().__init__(url)
        self.url = url
        self.root_folder = root_folder
        self.calnet_id = calnet_id
        self.passphrase = passphrase
    
    def scrape(self) -> None:
        # Configure Selenium Driver
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--enable-logging")
        driver = webdriver.Chrome(options=options)

        # Navigate to bCourses "Media" page and log in with CalNet
        driver.get(self.url[0])
        wait = WebDriverWait(driver, 10)
        calnet_id_field = wait.until(EC.presence_of_element_located((By.ID, 'username')))  
        passphrase_field = wait.until(EC.presence_of_element_located((By.ID, 'password')))

        calnet_id_field.send_keys(self.calnet_id)
        passphrase_field.send_keys(self.passphrase)

        sign_in_button = wait.until(EC.element_to_be_clickable((By.ID, 'submit')))
        sign_in_button.click()

        time.sleep(10)

        wait.until(EC.url_to_be(self.url[0]))
        wait = WebDriverWait(driver, 30)

        for i in range(len(self.url)):
            curr_url = self.url[i]
            curr_root_folder = self.root_folder[i]
            create_and_enter_dir(curr_root_folder)
            self.content_extract(curr_root_folder, curr_url, driver)

        # Close the browser
        driver.quit()

    def content_extract(self, filename, url, driver):
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.url_to_be(url))

        # Click "Load More" buttons
        while True:
            try:
                iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tool_launch")))
                driver.switch_to.frame(iframe)
                
                load_more_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Load More')]")))
                load_more_button.click()
                print("Clicked 'Load More' button.")
                
                time.sleep(5)
                driver.switch_to.default_content()
                
            except Exception as e:
                break

        print("Loaded all videos")

        time.sleep(2)

        try:
            # Find all videos
            ul_element = driver.find_element(By.ID, 'gallery')
            li_elements = ul_element.find_elements(By.CLASS_NAME, 'galleryItem')

            # Open each video link in a new tab and process
            for li in li_elements:
                try:
                    # Collect video title
                    div_element = li.find_element(By.CSS_SELECTOR, 'div.photo-group.thumb_wrapper')
                    title = div_element.get_attribute('title')

                    # Collect video upload date
                    thumb_time_added_element = li.find_element(By.CLASS_NAME, 'thumbTimeAdded')
                    date_span = thumb_time_added_element.find_element(By.CSS_SELECTOR, 'span[aria-label]')
                    date_text = date_span.get_attribute('aria-label')

                    # Define subfolder name and navigate inside
                    folder_name = self.sanitize_title(title + " " + date_text)
                    original_directory = os.getcwd()
                    create_and_enter_dir(folder_name)

                    # Find the video link and open in new tab
                    link_element = li.find_element(By.CLASS_NAME, 'item_link')
                    link = link_element.get_attribute('href')
                    driver.execute_script("window.open(arguments[0], '_blank');", link)
                    
                    # Switch to the new tab
                    new_tab_handle = driver.window_handles[-1]
                    driver.switch_to.window(new_tab_handle)
                    
                    # Wait for the page to load
                    time.sleep(5)

                    current_url = driver.current_url
                    self.metadata_extract(self.sanitize_title(title), date_text, current_url)

                    # Locate and click the "Show Transcript" link
                    show_transcript_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.transcript-body-open'))
                    )
                    show_transcript_link.click()

                    # Wait for the transcript body to be visible
                    transcript_body_div = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.transcript-body'))
                    )

                    # Find all span elements with class 'transcription-time-part' inside the div
                    time_parts = transcript_body_div.find_elements(By.CSS_SELECTOR, 'span.transcription-time-part')

                    # Open a markdown file for writing
                    output_file_path = 'transcript.md'
                    with open(output_file_path, 'w', encoding='utf-8') as file:
                        # Iterate through each span and get the start time, end time, and text
                        for time_part in time_parts:
                            start_time = time_part.get_attribute('data-time-start')
                            end_time = time_part.get_attribute('data-time-end')
                            inner_span = time_part.find_element(By.CSS_SELECTOR, 'span')
                            text = inner_span.text.strip()
                            
                            # Format the line in markdown format
                            line = f"{start_time} - {end_time}: {text}\n"
                            
                            # Write the line to the file
                            file.write(line)

                    # Switch to correct frame and get video URL
                    driver.switch_to.frame("kplayer_ifp")
                    video_element = driver.find_element(By.CLASS_NAME, "persistentNativePlayer")
                    video_url = video_element.get_attribute("src")

                    #Download video from video_url
                    filename_m3u8 = title + ".m3u8"
                    self.download_m3u8(filename_m3u8, video_url)

                    # Convert the downloaded .m3u8 file to .mp4
                    self.convert_m3u8_to_mp4(filename_m3u8)

                    # Go back to root folder
                    os.chdir(original_directory)

                    # Close tab, switch back to original tab, and switch to correct frame
                    driver.close()
                    original_tab_handle = driver.window_handles[0]
                    driver.switch_to.window(original_tab_handle)
                    iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tool_launch")))
                    driver.switch_to.frame(iframe)

                except Exception as e:
                    print(f"{e}")
                    os.chdir(original_directory)
                    driver.close()
                    original_tab_handle = driver.window_handles[0]
                    driver.switch_to.window(original_tab_handle)
                    iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tool_launch")))
                    driver.switch_to.frame(iframe)
        except Exception:
            print("No videos available")

    def metadata_extract(self, filename, date, url):
        yaml_content = f"Video upload date: {date}\nLink: {url}"
        save_to_file(f'{filename}_metadata.yaml', yaml_content)

    def download_m3u8(self, filename_m3u8, video_url):
        # Download the video from the URL
        response = requests.get(video_url, stream=True)

        # Save the video content to a file
        with open(filename_m3u8, 'wb') as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)

        print(f"Video downloaded and saved as {filename_m3u8}")

    def convert_m3u8_to_mp4(self, filename_m3u8):
        # Adjusted pattern to match all URLs
        pattern = r'#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=\d+,RESOLUTION=\d+x\d+\n(http[s]?://[^\s]+)'
        try:
            with open(filename_m3u8, 'r') as textfile:
                text = textfile.read()

            matches = re.findall(pattern, text)

            if matches:
                media_url = matches[0]
                media_file = filename_m3u8.replace('.m3u8', '.mp4').replace(' ', '')

                cmdstring = f"ffmpeg -i \"{media_url}\" -bsf:a aac_adtstoasc -vcodec copy -c copy -crf 50 \"{media_file}\""
                print(f"Running command: {cmdstring}")

                # Execute ffmpeg command
                process = subprocess.Popen(cmdstring, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    print(f"ffmpeg conversion error: {stderr.decode()}")
                else:
                    print(f"Video converted and saved as {media_file}")
                    os.remove(filename_m3u8)

            else:
                print(f"No matching media URL found in {filename_m3u8}")

        except Exception as e:
            print(f"Error processing file {filename_m3u8}: {e}")

    def sanitize_title(self, title):
        # Replace characters that are not allowed in filenames
        title = re.sub(r'[,\/\\\:\*\?\"\<\>\|]', '', title)  # Remove invalid characters
        title = title.replace(' ', '_')  # Replace spaces with underscores
        return title

if __name__ == "__main__":
    root_folder = ["eecs106b", "cs61b"]
    url = ["https://bcourses.berkeley.edu/courses/1533392/external_tools/90481", "https://bcourses.berkeley.edu/courses/1532474/external_tools/90481"]
    calnet_id = 'calnet_id'
    passphrase = 'passphrase'

    scraper = ScrapebCourses(url, root_folder, calnet_id, passphrase)
    scraper.scrape()
