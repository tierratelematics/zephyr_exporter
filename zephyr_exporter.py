""" Ugly Jira XML parser for Zephyr tests """

from StringIO import StringIO
from pprint import pprint
from bs4 import BeautifulSoup
from html2rest import html2rest
from HTMLParser import HTMLParser
import csv
import glob
from copy import deepcopy

existing_ce_labels = [
    'FEP',
    'Device',
    'UI'
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


def summary_truncate(row, long_summary, key):
        if len(row['summary']) > 250:
            long_summary.append(key)
            # do not loss data on export (we'll adjust manually)
            row['description'] = row['summary']
            row['summary'] = row['summary'][:250]


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
    labels = list(existing_ce_labels)
    long_summary = []
    skipped = []

    parser = HTMLParser()

    for xml_file_name in glob.glob('*.xml'):
        with open(xml_file_name, 'r') as xml_file:
            xml_file_contents = xml_file.read()
            ddd = BeautifulSoup(xml_file_contents, 'html.parser')
            items = ddd.find_all('item')

            for item in items:
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
                summary = parser.unescape(
                    item.summary.get_text().encode('utf-8')).strip('CLONE - ')
                row['summary'] = summary
                description = parser.unescape(_restify(
                    item.description.get_text()))
                row['description'] = description
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
                # row['scenario'] = ''
                # if 'positive' in row_labels:
                #     row['scenario'] = 'positive'
                # elif 'negative':
                #     row['scenario'] = 'negative'

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
                step_tags = steps_elem.find_all('step',recursive=False)

                #NO multistep tests
                if len_steps == 2:
                    if '@positive' in description:
                        row['scenario'] = 'Positive'
                    elif '@negative' in description:
                        row['scenario'] = 'Negative'

                    # row['steps'] = parser.unescape(_restify(
                    #     step_tags[0].find('step').get_text()))
                    row['data'] = parser.unescape(_restify(
                        step_tags[0].find('data').get_text()))
                    # row['result'] = parser.unescape(_restify(
                    #     step_tags[0].find('result').get_text()))
                    summary_truncate(row, long_summary, key)
                    results.append(row)


                # Multistep tests
                # For each step, zephyr create two 'step' tag
                elif len_steps > 2:

                    multisteps.append(key)

                    for index, step in enumerate(step_tags, start=1):
                        # deepcopy required to avoid rows overriding
                        sub_row = deepcopy(row)

                        expected_result = parser.unescape(
                            _restify(step.find('result').get_text()))

                        if '@positive' in expected_result:
                            row['scenario'] = 'Positive'
                        elif '@negative' in expected_result:
                            row['scenario'] = 'Negative'

                        row['description'] = expected_result
                        # sub_row['steps'] = parser.unescape(_restify(
                        #     step.find('step').get_text()))
                        sub_row['data'] = parser.unescape(_restify(
                            step.find('step').get_text()))
                        # sub_row['result'] = parser.unescape(
                        #     _restify(step.find('result').get_text()))

                        sub_row['summary'] = summary + ' ' + str(index) +\
                                         '/' + str(len_steps/2)
                        summary_truncate(sub_row, long_summary, key)

                        results.append(sub_row)

                        #Check for empty 'steps' or 'result' values
                        # if sub_row['steps'] != '\n* \n' or sub_row['result'] != '\n* \n':
                        #     results.append(sub_row)

            field_names = results[0].keys()
            preferred_order = ['sections', 'summary', 'labels', 'components']
            # ugly ordering
            for column_name in reversed(preferred_order):
                field_names.remove(column_name)
                field_names.insert(0, column_name)
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
    print "********* total jira tests({0}) ******************".format(
        len(items))
    print "********* multisteps tests ({0}) ******************".format(
        len(multisteps))
    pprint(multisteps)
    print "********* test cases created ({0}) ******************".format(
        len(results))

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
    labels = labels[:len(existing_ce_labels)] + sorted(
        list(set([label.encode('utf-8') for label in
                  labels[len(existing_ce_labels)+1:]])),
        key=str.lower)
    for index, label in enumerate(labels, start=1):
        print "{0},{1}".format(index, label)









if __name__ == '__main__':
    parse_xml()




# TODO:
# manual fix /* on SS
# set comments on custom field?
