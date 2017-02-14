""" Ugly Jira XML parser for Zephyr tests """

from StringIO import StringIO
from pprint import pprint
from bs4 import BeautifulSoup
from html2rest import html2rest


def parse_xml():
    def _restify(text):
        stream = StringIO()
        html2rest(text.replace('*', '\n*').encode('utf-8'), writer=stream)
        return stream.getvalue()

    with open('tests.xml', 'r') as xml_file:
        xml_file_contents = xml_file.read()
        ddd = BeautifulSoup(xml_file_contents, 'html.parser')
        results = []
        multisteps = []
        has_comments = []
        has_attachments = []
        no_steps = []
        labels = []

        for item in ddd.find_all('item'):
            row = {}
            key = item.key.get_text()
            row['key'] = key
            row['summary'] = item.summary.get_text()
            row['description'] = _restify(item.description.get_text())
            row['link'] = item.link.get_text()
            row['priority'] = item.priority.get_text()
            row['reporter'] = item.reporter.get_text()
            row['labels'] = [label.get_text() for label in
                             item.find_all('label')]
            labels.extend(row['labels'])
            row['links'] = [link.get_text() for link in
                            item.find_all('issuekey') if
                            link.parent.parent.get('description') == 'tests']
            row['attachments'] = [attachment.get('name') for attachment in
                                  item.find_all('attachment') if
                                  attachment.get('name')]

            if row['attachments']:
                has_attachments.append(key)
            if item.find('comment') is not None:
                has_comments.append(key)

            steps_elem = item.find('steps')
            if steps_elem is None:
                len_steps = 0
                no_steps.append(key)
            else:
                len_steps = len(steps_elem.find_all('step'))

            if len_steps > 2:
                # no multisteps import
                multisteps.append(key)
            elif len_steps == 2:
                steps = item.find('steps')
                row['steps'] = _restify(
                    steps.find('step').find('step').get_text()
                )
                row['data'] = _restify(steps.find('data').get_text())
                row['result'] = _restify(steps.find('result').get_text())

            if key not in multisteps:
                results.append(row)

        labels = sorted(list(set(labels)), key=str.lower)

        print "********* results ({0}) ******************".format(
            len(results))
        print pprint(results)

        print "********* has comments ({0}) ******************".format(
            len(has_comments))
        print pprint(has_comments)

        print "********* has attachments ({0}) ******************".format(
            len(has_attachments))
        print pprint(has_attachments)

        print "********* no steps ({0}) ******************".format(
            len(no_steps))
        print pprint(no_steps)

        print "********* multisteps ({0}) ******************".format(
            len(multisteps))
        print pprint(multisteps)

        print "********* labels ({0}) ******************".format(
            len(labels))
        print pprint(labels)

if __name__ == '__main__':
    parse_xml()


# TODO:
# clean labels
