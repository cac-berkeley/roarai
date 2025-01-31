from pathlib import Path
import yaml
import json
from rag.file_conversion_router.conversion.base_converter import BaseConverter
from rag.file_conversion_router.classes.page import Page
from rag.file_conversion_router.classes.chunk import Chunk

class EdConverter(BaseConverter):
    def __init__(self):
        super().__init__()

    # Override
    def _to_markdown(self, input_path: Path, output_path: Path) -> Path:
        """Perform Json to Markdown conversion.

        Arguments:
        input_path -- Path to the input json file.
        output_folder -- Path to the folder where the output md file will be saved.
        """
        # call on scrape.py's modified json converter + load the json_data
        output_path = output_path.with_suffix(".md")
        with open(input_path, 'r') as file:
            json_data = json.load(file)
        
        # filter the json so only good data remains -- comment out if filter not needed/wanted!
        json_data = json_kb_filter(json_data)

        # run the ed scraper
        scrape_json(json_data, output_path)
        return output_path
    
    def _to_page(self, input_path: Path, output_path: Path) -> Page:
        """Perform Markdown to Page conversion."""
        try:
            input_path = self._to_markdown(input_path, output_path)
        except Exception as e:
            self._logger.error(f"An error occurred during markdown conversion: {str(e)}")
            raise

        output_path.parent.mkdir(parents=True, exist_ok=True)

        filetype = input_path.suffix.lstrip('.')
        with open(input_path, "r") as input_file:
            text = input_file.read()

        metadata_path = input_path.with_name(f"{input_path.stem}_metadata.yaml")
        metadata_content = self._read_metadata(metadata_path)
        url = metadata_content.get("URL")
        return Page(pagename=input_path.stem, content={'text': text}, filetype=filetype, page_url=url)

# recursive filter for json data
def json_kb_filter(data):
    debug_lst = []
    ret = []
    for elem in data:
        lowered = elem["text"].lower()

        submission_words = 0
        for word in ["gradescope", "submi", "extension", "autograder", "slip day", "exception"]:
            submission_words += lowered.count(word)
        first_person_words = 0
        for word in [" i ", " i'", " me ", " my ", " mine "]:
            first_person_words += lowered.count(word)
        dated_question = False
        for word in ["submi", "post", "release", "due"]:
            if "when" in lowered and word in lowered:
                dated_question = True
        if "publish" in lowered and " be " in lowered:
            dated_question = True
        short_query = len(lowered.split(" ")) < 10

        if "answers" in elem and len(elem["answers"]) > 0:
            elem["answers"] = json_kb_answers_filter(elem["answers"], debug_lst)
            # filters out private technical queries too, but fine for now
            if elem["private"] == True:
                elem["url"] += " -- Private post"
                debug_lst.append(elem)
            elif ("waitlist" in lowered or submission_words > 1) and first_person_words > 2:
                elem["url"] += " -- Personal post"
                debug_lst.append(elem)
            elif dated_question or (short_query and "release" in lowered):
                elem["url"] += " -- Dated question"
                debug_lst.append(elem)
            elif len(elem["answers"]) > 0:
                ret.append(elem)
            else:
                elem["url"] += " -- Answerless"
                debug_lst.append(elem)
        if "comments" in elem and len(elem["comments"]) > 0:
            elem["comments"] = json_kb_comments_filter(elem["comments"], debug_lst)
            if elem["private"] == True:
                elem["url"] += " -- Private post"
                debug_lst.append(elem)
            elif len(elem["comments"]) > 0 or elem["user"]["role"] == "admin":
                ret.append(elem)
            else:
                elem["url"] += " -- Commentless"
                debug_lst.append(elem)

    return ret

# filters all comments - takes and recieves a list of comments
def json_kb_comments_filter(data, debug_lst=None):
    ret = []
    for comment in data:
        lowered = comment["text"].lower()

        # helper variables
        first_person_words = 0
        for elem in [" i ", " i'", " me ", " my ", " mine "]:
            first_person_words += lowered.count(elem)
        submission_words = 0
        for elem in ["gradescope", "submi", "extension", "autograder", "slip day", "exception"]:
            submission_words += lowered.count(elem)
        dated_question = False
        for word in ["submi", "post", "release", "due"]:
            if "when" in lowered and word in lowered:
                dated_question = True
        if "publish" in lowered and " be" in lowered:
            dated_question = True
        is_question = any([elem in lowered for elem in [" can ", "could", "who", "what", "when", "where", "why", "how", "?"]])
        popular_comment = comment["votes"] > 0 or any([elem["user"]["role"] == "student" for elem in comment["comments"]])
        short_query = len(lowered.split(" ")) < 15

        # filter parameters!
        if comment["user"]["role"] == "admin":
            comment["comments"] = json_kb_comments_filter(comment["comments"], debug_lst)
            ret.append(comment)
        elif len(comment["comments"]) == 0  and not popular_comment:
            comment["url"] += " -- Last (Unpopular) Comment"
            debug_lst.append(comment)
        elif first_person_words > 2 and not popular_comment:
            comment["url"] += " -- Personal request"
            debug_lst.append(comment)
        elif submission_words > 1:
            comment["url"] += " -- Gradesope request"
            debug_lst.append(comment)
        elif dated_question or (short_query and "release" in lowered):
            comment["url"] += " -- Dated question"
            debug_lst.append(comment)
        # special case! if the comment is a question with responses, prune some conditionally
        elif is_question:
            admin_res = any([res["user"]["role"] == "admin" for res in comment["comments"]])
            for res in comment["comments"]:
                # if there's an admin response and this "res" is unpopular, prune it
                if admin_res and len(res["comments"]) + res["votes"] == 0 and res["user"]["role"] != "admin":
                    comment["url"] += " -- Tangential comment"
                    debug_lst.append(comment)
                else:
                    ret.append(comment)

                if "comments" in res and len(res["comments"]) > 0:
                    res["comments"] = json_kb_comments_filter(res["comments"], debug_lst)
        else:
            comment["comments"] = json_kb_comments_filter(comment["comments"], debug_lst)
            ret.append(comment)
    return ret

# filters all answers - takes and recieves a list of answers
def json_kb_answers_filter(data, debug_lst=None):
    ret = []
    admin_res = any([res["user"]["role"] == "admin" for res in data])

    for res in data:
        popular_comment = res["votes"] > 0 or ("comments" in res and len(res["comments"]) > 0)

        # filter parameters!
        if res["user"]["role"] == "admin":
            res["comments"] = json_kb_comments_filter(res["comments"], debug_lst)
            ret.append(res)
        elif admin_res and not popular_comment:
            debug_lst.append(res)
        else:
            res["comments"] = json_kb_comments_filter(res["comments"], debug_lst)
            ret.append(res)

    return ret

def scrape_json(json_data, output_path: Path) -> Path:
    # Convert JSON data to Markdown
    markdown_content = convert_json_to_markdown(json_data)
    # Save Markdown content to output.md
    save_markdown(markdown_content, output_path) 

def convert_json_to_markdown(data):
    markdown = ""
    for item in data:
        markdown += f"# {item['title']}\n"
        markdown += f"**User:** {item['user']['name']}\n"
        markdown += f"**Role:** {item['user']['role']}\n"
        markdown += f"**URL:** {item['url']}\n"
        markdown += f" {item['text']}\n"

        if len(item.get("comments", [])) > 0:
            for comment in item.get("comments", []):
                markdown += "### Comment\n"
                markdown += f"**User:** {comment['user']['name']}\n"
                markdown += f"**Role:** {comment['user']['role']}\n"
                markdown += f"**URL:** {comment['url']}\n"
                markdown += f"{comment['text']}\n"
                if "comments" in comment and len(comment.get("comments", [])) > 0:
                    markdown += process_comments(comment["comments"])
        if len(item.get("answers", [])) > 0:
            for answer in item.get("answers", []):
                markdown += "### Answer \n"
                markdown += f"**Name:** {answer['user']['name']}\n"
                markdown += f"**Role:** {answer['user']['role']}\n"
                markdown += f"**URL:** {answer['url']}\n"
                markdown += f"{answer['text']}\n"
                if "comments" in answer and len(answer.get("comments", [])) > 0:
                    markdown += process_comments(answer["comments"])

    return markdown

### UTILITY FUNCTIONS ###
def save_markdown(markdown_content, file_path):
    with open(file_path, 'w') as file:
        file.write(markdown_content)

def process_comments(comments):
    markdown = ""
    for comment in comments:
        markdown += f"**User:** {comment['user']['name']}\n"
        markdown += f"**Role:** {comment['user']['role']}\n"
        markdown += f"**URL:** {comment['url']}\n"
        markdown += f"{comment['text']}\n"
        if "comments" in comment and len(comment.get("comments", [])) > 0:
            markdown += process_comments(comment["comments"])
            markdown += '\n'
    return markdown