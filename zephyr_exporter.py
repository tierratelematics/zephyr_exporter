""" Ugly Jira XML parser for Zephyr tests """

from StringIO import StringIO
from pprint import pprint
from bs4 import BeautifulSoup
from html2rest import html2rest
from HTMLParser import HTMLParser
import csv
import glob

existing_labels = [
    'FEP',
    'Device',
    'UI',
    'NTRIP',
    'FRED',
    'Types',
    'Models',
    'Platforms',
    'MeasurementUnits',
]


# after import fix labels on stories too
labels_mapping = {
    'Negative': 'negative',
    'neagtive': 'negative',
    'Positive': 'positive',
    'ComplexParameters': 'ComplexParameter',
    'omplexParameters': 'ComplexParameter',
    'ComplexParametersChecks': 'ComplexParameterChecks',
    'DEVICE': 'Device',
    'Subscription': 'Subscriptions',
    'User': 'Users',
    'Mobility': 'mobility',
    'KeyON/OFF': 'KeyOnOff',
    'GeoFence': 'GeoFence',
    'GeoFences': 'GeoFence',
    'GeoFenceProfile': 'GeoFence',
    'Geofence': 'GeoFence',
    'CanViewer': 'CANViewer',
    'CanBus': 'CANBus',
    'CanParameters': 'CANParameter',
    'CANParameters': 'CANParameter',
    'canReportConf': 'CANReportConf',
    'reportType': 'ReportType',
    'canPGNRequest': 'PGN',
    'pgn': 'PGN',
    'PGNRequest': 'PGN',
    'Curfew': 'Curfew',
    'CanBusRefresh': 'CANBusRefresh',
    'CanBusAlarms': 'CANBusAlarm',
    'Sanity': 'sanity',
    'Long_Test_Run': 'LongRunTest',
    'Failure': 'failure',
    'Exploratory': 'exploratory',
    'EquipmentUtilizationReport': 'EquipmentUtilization',
    'Engine_OnOff_Message': 'KeyOnOff',
    'KeyOnOffReport': 'KeyOnOff',
    'DigitalInputsAlarms': 'DigitalInputAlarm',
    'DigitalInputsCheck': 'DigitalInputCheck',
    'DigitalInputsProfile': 'DigitalInput',
    'DigitalInputsReport': 'DigitalInput',
    'UreaReport': 'Urea',
    'UreaReportExport': 'UreaExport',
    'Users': 'User',
    'VehicleDataReport': 'VehicleData',
    'SuperSignalStatusProfile': 'SuperSignalStatus',
    'SuperSignalStatusProfileConfiguration': 'SuperSignalStatusConfiguration',
    'SuperSignalProtocols': 'SuperSignalProtocol',
    'StatusProfile': 'Status',
    'PowerManagementProfile': 'PowerManagement',
    'DataProfile': 'CANBus',
    'CANBusProfile': 'CANBus',
    'Automated': 'automated',
    'Automatable': 'automatable',
}

labels_blacklist = [
    'S',
    'L',
    'Sprint5',
]


skipped_tests = [
]


def parse_xml():
    def _restify(text):
        stream = StringIO()
        if text and not text.startswith('*'):
            text = '*' + text
        html2rest(text.encode('utf-8'), writer=stream)
        return stream.getvalue().replace('*', '\n* ')

    results = []
    multisteps = []
    has_comments = []
    has_attachments = []
    no_steps = []
    no_labels = []
    no_links = []
    labels = list(existing_labels)
    long_summary = []
    skipped = []

    parser = HTMLParser()

    for xml_file_name in glob.glob('*.xml'):
        with open(xml_file_name, 'r') as xml_file:
            xml_file_contents = xml_file.read()
            ddd = BeautifulSoup(xml_file_contents, 'html.parser')

            for item in ddd.find_all('item'):
                row = {}
                key = item.key.get_text()

                if item.type.get_text() in ('Unit Test Case',) or \
                   key in skipped_tests:
                    skipped.append(key)
                    continue

                # manually set up folder/sections hierarchy
                row['sections'] = ''
                row['description'] = ''

                row['key'] = key
                row['summary'] = parser.unescape(
                    item.summary.get_text().encode('utf-8'))
                row['description'] = parser.unescape(_restify(
                    item.description.get_text()))
                row['link'] = item.link.get_text()
                row['priority'] = item.priority.get_text()
                row['reporter'] = item.reporter.get_text()
                row_labels = [labels_mapping.get(label.get_text(),
                                                 label.get_text())
                              for label in
                              item.find_all('label')
                              if label.get_text() not in labels_blacklist]
                labels.extend(row_labels)
                if not row_labels:
                    no_labels.append(key)
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
                    row['type'] = 'automated'
                elif 'Sanity' in row_labels:
                    row['type'] = 'sanity'
                else:
                    row['type'] = 'regression'

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
                if not row['links']:
                    no_links.append(key)

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
                    row['steps'] = parser.unescape(_restify(
                        steps.find('step').find('step').get_text()
                    ))
                    row['data'] = parser.unescape(
                        _restify(steps.find('data').get_text()))
                    row['result'] = parser.unescape(
                        _restify(steps.find('result').get_text()))

                if len(row['summary']) > 250:
                    long_summary.append(key)
                    # do not loss data on export (we'll adjust manually)
                    row['description'] = row['summary']
                    row['summary'] = row['summary'][:250]

                if key not in multisteps:
                    results.append(row)

            field_names = results[0].keys()
            with open('{0}.csv'.format(
                    xml_file_name[:-len('.xml')]), 'wb') as csvfile:
                writer = csv.DictWriter(csvfile,
                                        delimiter=';',
                                        quotechar='"',
                                        quoting=csv.QUOTE_ALL,
                                        fieldnames=field_names)

                writer.writeheader()
                for result in results:
                    writer.writerow(result)

    print "********* results ({0}) ******************".format(
        len(results))
    pprint(results)

    print "********* has comments ({0}) ******************".format(
        len(has_comments))
    pprint(has_comments)

    print "********* has attachments ({0}) ******************".format(
        len(has_attachments))
    pprint(has_attachments)

    print "********* no steps ({0}) ******************".format(
        len(no_steps))
    pprint(no_steps)

    print "********* multisteps ({0}) ******************".format(
        len(multisteps))
    pprint(multisteps)

    print "********* long summary ({0}) ******************".format(
        len(long_summary))
    pprint(long_summary)

    print "********* skipped ({0}) ******************".format(
        len(skipped))
    pprint(skipped)

    print "********* NO test links, no traceability ({0}) ********".format(
        len(no_links))
    pprint(no_links)

    print "********* NO labels ({0}) ******************".format(
        len(no_labels))
    pprint(no_labels)

    print "********* testrail labels ({0}) ******************".format(
        len(set(labels)))

    # we have to maintain existing labels and indexes already there
    # in testrail...
    labels = labels[:len(existing_labels)] + sorted(
        list(set([label.encode('utf-8') for label in
                  labels[len(existing_labels)+1:]])),
        key=str.lower)
    for index, label in enumerate(labels, start=1):
        print "{0},{1}".format(index, label)


if __name__ == '__main__':
    parse_xml()


# TODO:
# manual fix /* on SS
# set comments on custom field?
