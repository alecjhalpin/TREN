from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.labels=[];self.tabs=[];self.panes=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='label':self.labels.append(a.get('for'))
        if 'data-tab' in a:self.tabs.append(a['data-tab'])
        if 'data-pane' in a:self.panes.append(a['data-pane'])

class UiStructureTests(unittest.TestCase):
    def test_accessible_controls_and_all_existing_panes(self):
        html=(Path(__file__).resolve().parents[1]/'index.html').read_text();p=Page();p.feed(html)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertTrue(all(label in p.ids for label in p.labels))
        self.assertEqual(set(p.tabs),set(p.panes))
        self.assertEqual(set(p.tabs),{'chat','coding','web','memory','tasks','activity','settings'})
        for element in re.findall(r"\$\('([^']+)'\)",html):self.assertIn(element,p.ids)
        self.assertIn('<dialog id="codeDialog"',html)
