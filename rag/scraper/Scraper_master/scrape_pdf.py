from rag.scraper.Scraper_master.base_scraper import BaseScraper
import requests


class ScrapePdf(BaseScraper):
    """
    A class for scraping PDF files from the web, extending the functionality of BaseScraper.
    """

    def __init__(self, url):
        super().__init__(url)

    def content_extract(self, filename, url, **kwargs):
        """
        Downloads and saves a PDF from the initialized URL.
        """
        response = requests.get(self.url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"Download completed successfully and saved as {filename}")
        else:
            print(f"Failed to download the PDF. Status code: {response.status_code}")


# Example usage:
if __name__ == "__main__":
    pdf_url = "https://ucb-ee106.github.io/106b-sp23site/assets/hw/Homework_5__Grasping.pdf"  # Replace with the actual PDF URL
    pdf_saver = ScrapePdf(pdf_url)  # Specify the filename to save as
    pdf_saver.content_extract("HW5", pdf_url) # Start the download process
