""" Ugly Jira XML parser for Zephyr tests """

from StringIO import StringIO
from pprint import pprint
from bs4 import BeautifulSoup
from html2rest import html2rest
import csv


labels_mapping = {
    'Negative': 'negative',
    'neagtive': 'negative',
    'Positive': 'positive',
    'omplexParameters': 'ComplexParameters',
    'DEVICE': 'Device',
    'Subscription': 'Subscriptions',
    'User': 'Users',
    'Mobility': 'mobility',
    'KeyON/OFF': 'KeyOnOff',
    'GeoFence': 'GeoFences',
    'CanViewer': 'CANViewer',
    'CanBus': 'CANBus',
    'CanParameters': 'CANParameters',
    'canPGNRequest': 'CANPGNRequest',
    'canReportConf': 'CANReportConf',
}

labels_blacklist = [
    'S',
    'L',
    'Sprint5',
]


def parse_xml():
    def _restify(text):
        stream = StringIO()
        if text and not text.startswith('*'):
            text = '*' + text
        html2rest(text.encode('utf-8'), writer=stream)
        return stream.getvalue().replace('*', '\n* ')

    with open('tests.xml', 'r') as xml_file:
        xml_file_contents = xml_file.read()
        ddd = BeautifulSoup(xml_file_contents, 'html.parser')
        results = []
        multisteps = []
        has_comments = []
        has_attachments = []
        no_steps = []
        labels = []
        long_summary = []

        for item in ddd.find_all('item'):
            row = {}
            key = item.key.get_text()

            # manually set up folder/sections hierarchy
            row['sections'] = ''
            row['description'] = ''

            row['key'] = key
            row['summary'] = item.summary.get_text().encode('utf-8')
            row['description'] = _restify(item.description.get_text())
            row['link'] = item.link.get_text()
            row['priority'] = item.priority.get_text()
            row['reporter'] = item.reporter.get_text()
            row_labels = [labels_mapping.get(label.get_text(),
                                             label.get_text())
                          for label in
                          item.find_all('label')
                          if label not in labels_blacklist]
            labels.extend(row_labels)
            row['labels'] = ', '.join(row_labels)

            # initialize custom field scenario
            row['scenario'] = ''
            if 'positive' in row_labels:
                row['scenario'] = 'positive'
            elif 'negative':
                row['scenario'] = 'negative'

            # initialize custom field type
            row['type'] = ''
            if 'Automated' in row_labels:
                row['type'] = 'Automated'
            elif 'Sanity' in row_labels:
                row['type'] = 'Sanity'
            else:
                row['type'] = 'Regression'

            # initialize custom field components
            components = []
            if 'UI' in row_labels:
                components.append('UI')
            if 'FEP' in row_labels:
                components.append('FEP')
            if 'BE' in row_labels:
                components.append('BE')
            if 'E2E' in row_labels:
                components.append('E2E')
            row['components'] = ', '.join(components)

            row['links'] = ', '.join(
                [link.get_text() for link in
                 item.find_all('issuekey') if
                 link.parent.parent.get('description') == 'tests'])
            row['attachments'] = ', '.join(
                [attachment.get('name') for attachment in
                 item.find_all('attachment') if
                 attachment.get('name')])

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

            if len(row['summary']) > 250:
                long_summary.append(key)
                # do not loss data on export (we'll adjust manually)
                row['description'] = row['summary']
                row['summary'] = row['summary'][:250]

            if key not in multisteps:
                results.append(row)

        field_names = results[0].keys()
        with open('output.csv', 'wb') as csvfile:
            writer = csv.DictWriter(csvfile,
                                    delimiter=';',
                                    quotechar='"',
                                    quoting=csv.QUOTE_ALL,
                                    fieldnames=field_names)

            writer.writeheader()
            for result in results:
                writer.writerow(result)

        labels = sorted(
            list(set([label.encode('utf-8') for label in labels])),
            key=str.lower)

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

        print "********* long summary ({0}) ******************".format(
            len(long_summary))
        print pprint(long_summary)

        print "********* labels ({0}) ******************".format(
            len(labels))
        print pprint(labels)

if __name__ == '__main__':
    parse_xml()


# TODO:
# manual fix /* on SS
# set comments on custom field?
