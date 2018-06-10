import argparse
import logging
import re
import os
import pickle
import io_utils

from log_statement import LogStatement


__author__ = 'hlib'

LOG_LEVEL_REGEX = re.compile(".*([Ll]og|LOG|[Ll]ogger|LOGGER)\.([Tt]race|[Dd]ebug|[Ii]nfo|[Ww]arn|[Ee]rror|[Ff]atal)\(.*")

VAR_PLACEHOLDER = "<VAR>"
STRING_RESOURCE_PLACEHOLDER = "<STRING_RESOURCE>"

def extract_log_level(line):
    matcher = re.match(LOG_LEVEL_REGEX, line)
    if matcher is not None:
        return matcher.group(2).lower()
    else:
        print("Log level couldn't be extracted from log statement: " + line)
        return "Unknown"

def extract_text_and_variables(line):
    full_line = line
    text = ""
    text_parts = 0
    opening_quote_index = line.find("\"")
    while opening_quote_index >= 0:
        line = line[opening_quote_index + 1:]
        closing_quote_index = line.find("\"")
        if closing_quote_index < 0:
            print("No closing quote found for the opening quote in string: " + full_line)
            return full_line, "", 0
        text += line[:closing_quote_index]
        text_parts += 1
        line = line[closing_quote_index+1:]
        opening_quote_index = line.find("\"")
    if line.find("+") >= 0:
        text_parts += 1
    if text_parts > 1:
        n_variables = text_parts - 1
    else:
        n_variables = text.count("{}")
        if n_variables == 0:
            n_variables = text.count("%")
    return full_line, text, n_variables


def contains_text(line):
    return line.find("\"") >= 0

def append_period_if_absent(line):
    if len(line) > 0:
        if line[-1] not in ['.', '!', '?']:
            line += "."
    return line


def replace_string_resources_names(line):
    changed = re.sub('^([0-9a-zA-Z]+\\.)+[0-9a-zA-Z]+$', STRING_RESOURCE_PLACEHOLDER, line)
    # if changed != line:
    #     print(line + "  ----->  " + changed)
    return changed


def replace_variable_place_holders(line):
    changed = re.sub('\\{\\}', VAR_PLACEHOLDER, line)
    changed = re.sub('%[0-9]*[a-z]', VAR_PLACEHOLDER, changed)
    # if changed != line:
    #     print(line + "  ----->  " + changed)
    return changed


def postprocess_extracted_text(line):
    line = line.strip()
    line = replace_string_resources_names(line)
    line = replace_variable_place_holders(line)
    # line = append_period_if_absent(line)
    return line


STOP_REGEX = re.compile(".*is(Trace|Debug|Info|Warn)Enabled.*")

def filter_bad_context_line(new_context_line):
    return re.match(STOP_REGEX, new_context_line) is None


def read_grepped_log_file(directory, min_log_number_per_project):
    list= []
    project_stats = {}
    print("returning logs from projects with more than " + str(min_log_number_per_project) + " logs extracted")
    for filename in os.listdir(directory):
        log_counter = 0
        current_proj_list = []
        try:
            with open(os.path.join(directory, filename), 'r') as f:
                n_lines_of_context = int(f.readline())
                while True:
                    #reading github link
                    github_link = f.readline()
                    if not github_link:
                        break

                    context_before = []
                    for i in range(n_lines_of_context):
                        new_context_line = f.readline()
                        if filter_bad_context_line(new_context_line):
                            context_before.append(new_context_line)
                    #reading log statement
                    log_statement_line = f.readline()
                    context_after = []
                    for i in range(n_lines_of_context):
                        new_context_line = f.readline()
                        if filter_bad_context_line(new_context_line):
                            context_after.append(new_context_line)

                    #reading 2 empty lines
                    f.readline()
                    f.readline()
                    if contains_text(log_statement_line):
                        current_proj_list.append({'log_statement': log_statement_line,
                                                  'context_before': context_before,
                                                  'context_after': context_after,
                                     'github_link': github_link, 'project': filename[:filename.index('.')]})
                        log_counter += 1
        except UnicodeDecodeError as er:
            print(er)
            print('Error in file: ' + filename + ". Skipping it.")
            print('The problem occured with log number ' + str(log_counter))

        project_stats[filename] = log_counter
        if log_counter >= min_log_number_per_project:
            list.extend(current_proj_list)
    return list, project_stats

def remove_placeholders(log_text):
    log_text = re.sub(VAR_PLACEHOLDER, r'', log_text)
    log_text = re.sub(STRING_RESOURCE_PLACEHOLDER, r'', log_text)
    return log_text

def split_log_text_to_keywords_and_identifiers(line):
    return list(filter(None, re.split("[\[\] ,.\-!?:\n\t(){};=+*/\"&|<>_#\\\@$]+", line)))


def get_words_from_log_text(log_text):
    #Consider different splitting for log statement than for the context
    log_text = remove_placeholders(log_text)
    log_text = log_text.lower()
    return split_log_text_to_keywords_and_identifiers(log_text)


def process_log_statement(log_entry):
    log_text_line, text, n_variables = extract_text_and_variables(log_entry['log_statement'])
    log_text = postprocess_extracted_text(text)
    words_from_log_text = get_words_from_log_text(log_text)
    words_from_log_text = filter_out_stop_words(words_from_log_text)
    return LogStatement(
            text_line=log_text_line,
            text=log_text,
            text_words=words_from_log_text,
            level=extract_log_level(log_entry['log_statement']),
            n_variables=n_variables,
            context_before=log_entry['context_before'],
            context_after=log_entry['context_after'],
            project = log_entry['project'],
            link=log_entry['github_link'])

STOP_WORDS=["a", "an", "and", "are", "as", "at", "be", "for", "has", "in", "is", "it", "its", "of", "on", "that",
            "the", "to", "was", "were", "with"]
#the following words are normally stop words but we might want not to consider as stop words:  by, from, he, will

def filter_out_stop_words(words_from_log_text):
    return list(filter(lambda w: w not in STOP_WORDS, words_from_log_text))

def filter_empty_logs(pp_logs):
    return list(filter(lambda l: len(l.text_words) > 0 and len(l.context.context_before) > 0
                ,pp_logs))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('--min-log-number-per-project', action='store', type=int, default=100)
    args = parser.parse_args()

    in_file = "../.Logs"
    grepped_logs, project_stats = read_grepped_log_file(in_file, args.min_log_number_per_project)
    pp_logs = []
    logs_total = len(grepped_logs)
    for ind, grepped_log in enumerate(grepped_logs):
        pp_logs.append(process_log_statement(grepped_log))
        logging.info(f"Processing {ind} log out of {logs_total} ({ind * 100.0 / logs_total:.4}%)")
    pp_logs = filter_empty_logs(pp_logs)

    io_utils.dump_preprocessed_logs(pp_logs)
    io_utils.dump_project_stats(project_stats)
