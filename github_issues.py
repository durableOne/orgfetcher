from github3 import login
from orgmunge.classes import Heading, Headline, TimeStamp, ORG_TIME_FORMAT, Scheduling
from orgfetcher import Fetcher, Transformer, Updater
from datetime import datetime as dt
from typing import Tuple
import re
import os


class GithubIssuesFetcher(Fetcher):
    def __init__(self, creds_file: str):
        token = self._get_token(creds_file)
        github = login(token=token)
        super().__init__(github=github)
    def _get_token(self, token_file: str):
        with open(token_file, 'r') as IN:
            return IN.read().strip()
    def fetch(self):
        repos = self.github.repositories()
        issues = {repo: [i for i in repo.issues(state='all')] for repo in repos}
        if any(v for v in issues.values()):
            self.data = {repo: {'issues': [[issue.title, issue.url, issue.closed_at, issue.state]
                                         for issue in issues[repo]],
                                'languages': list(repo.languages()),}
                         for repo in repos}
            self.data = {k: v for k, v in self.data.items() if v}            
        else:
            self.data = dict()
        self.data_ready = True

class GithubIssuesTransformer(Transformer):
    def __init__(self, fetcher: GithubIssuesFetcher, *args, **kwargs):
        super().__init__(fetcher)
    def transform(self, issue_title: str, issue_url: str, closed_at: dt, state: str, lang: str) -> Heading:
        issue_url = re.sub(r'api.github.com/repos', 'github.com', issue_url) # So we get a link that works in the browser
        todo = self.todos['done_states']['done'] if state == 'closed' else self.todos['todo_states']['todo']
        headline = Headline(self.todos, '* ', title=f'[[{issue_url}][{issue_title}]]', todo=todo)
        heading = Heading(headline, (None, None, None))
        heading.properties['agenda-group'] = self._get_pretty_lang(lang) # For org-super-agenda
        if closed_at is not None:
            heading.scheduling = Scheduling('closed', TimeStamp(f'[{closed_at.astimezone().strftime(ORG_TIME_FORMAT)}]'))
        return heading
    def _get_pretty_lang(self, lang: str) -> str:
        langs = {'python': '🐍',
                 'perl': '🐪',
                 'emacs lisp': '𝛌',
                 'java': '☕'}
        l = langs.get(lang.lower())
        return (f'{l} ' if l else '') + lang
    def get_data(self):
        super().get_data()
        headings = {repo.name: [self.transform(*issue, self.data[repo]['languages'][0][0]) for issue in self.data[repo]['issues']]
                    for repo in self.data}
        self.transformed_data = headings
        self.data_ready = True

class GithubIssuesUpdater(Updater):
    def __init__(self, transformer: GithubIssuesTransformer, org_file_path:str):
        super().__init__(transformer, org_file_path)
        self.todos = self.transformer.todos

    def update_headings(self):
        super().update_headings()
        data = self.transformer.transformed_data
        for repo in data.keys():
            repo_heading = self.org_file.get_heading_by_path([repo])
            if not repo_heading:
                # Create a new top-level heading for this repo if it's new
                repo_heading = Heading(Headline(self.todos, '* ', title=repo), (None, None, None))
                self.org_file.root.add_child(repo_heading, new=True)
            issues = data[repo]
            open_issue_titles = [i.title for i in issues if i.todo in self.todos['todo_states']]
            open_issues_in_org_file = list(self.org_file.filter_headings(lambda h: h.parent is repo_heading and not h.done))
            open_issue_titles = [i.title for i in open_issues_in_org_file]
            closed_issues = [i for i in issues if i.todo in self.todos['done_states']]
            for i in open_issues_in_org_file:
                is_closed = [a for a in closed_issues if a.title == i.title]
                if is_closed:
                    i.todo = self.todos['done_states']['done']
                    i.scheduling.closed = is_closed[0].scheduling.closed
            for issue in issues:
                if issue.title not in open_issue_titles:
                    issue.level = 2
                    repo_heading.add_child(issue, new=True)
                    
CREDS_FILE = os.path.join(os.environ["HOME"], '.github_creds')
fetcher = GithubIssuesFetcher(CREDS_FILE)
transformer = GithubIssuesTransformer(fetcher)
updater = GithubIssuesUpdater(transformer, os.path.join(os.environ["HOME"], 'org', 'github.org'))
updater.update()
