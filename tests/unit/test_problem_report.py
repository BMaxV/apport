import datetime
import locale
import unittest, email, time

from io import BytesIO
import problem_report

bin_data = b'ABABABABAB\0\0\0Z\x01\x02'


class T(unittest.TestCase):
    def test_basic_operations(self):
        '''basic creation and operation.'''

        pr = problem_report.ProblemReport()
        pr['foo'] = 'bar'
        pr['bar'] = ' foo   bar\nbaz\n   blip  '
        pr['dash-key'] = '1'
        pr['dot.key'] = '1'
        pr['underscore_key'] = '1'
        self.assertEqual(pr['foo'], 'bar')
        self.assertEqual(pr['bar'], ' foo   bar\nbaz\n   blip  ')
        self.assertEqual(pr['ProblemType'], 'Crash')
        locale_time = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, "C")
        try:
            self.assertTrue(time.strptime(pr['Date']))
        finally:
            locale.setlocale(locale.LC_TIME, locale_time)
        self.assertEqual(pr['dash-key'], '1')
        self.assertEqual(pr['dot.key'], '1')
        self.assertEqual(pr['underscore_key'], '1')

    def test_ctor_arguments(self):
        '''non-default constructor arguments.'''

        pr = problem_report.ProblemReport('KernelCrash')
        self.assertEqual(pr['ProblemType'], 'KernelCrash')
        pr = problem_report.ProblemReport(date='19801224 12:34')
        self.assertEqual(pr['Date'], '19801224 12:34')

    def test_get_date(self):
        '''get_date() returns date.'''
        pr = problem_report.ProblemReport(date='Wed May 18 09:49:57 2022')
        self.assertEqual(pr.get_date(), datetime.datetime(2022, 5, 18, 9, 49, 57))

    def test_get_date_returns_none(self):
        '''get_date() returns None.'''
        pr = problem_report.ProblemReport()
        del pr['Date']
        self.assertEqual(pr.get_date(), None)

    def test_sanity_checks(self):
        '''various error conditions.'''

        pr = problem_report.ProblemReport()
        self.assertRaises(ValueError, pr.__setitem__, 'a b', '1')
        self.assertRaises(TypeError, pr.__setitem__, 'a', 1)
        self.assertRaises(TypeError, pr.__setitem__, 'a', (1,))
        self.assertRaises(TypeError, pr.__setitem__, 'a', ('/tmp/nonexistant', ''))
        self.assertRaises(TypeError, pr.__setitem__, 'a', ('/tmp/nonexistant', False, 0, True, 'bogus'))
        self.assertRaises(TypeError, pr.__setitem__, 'a', ['/tmp/nonexistant'])
        self.assertRaises(KeyError, pr.__getitem__, 'Nonexistant')

    def test_write(self):
        '''write() and proper formatting.'''

        pr = problem_report.ProblemReport(date='now!')
        pr['Simple'] = 'bar'
        pr['SimpleUTF8'] = '1äö2Φ3'.encode('UTF-8')
        pr['SimpleUnicode'] = '1äö2Φ3'
        pr['TwoLineUnicode'] = 'pi-π\nnu-η'
        pr['TwoLineUTF8'] = 'pi-π\nnu-η'.encode('UTF-8')
        pr['WhiteSpace'] = ' foo   bar\nbaz\n  blip  \n\nafteremptyline'
        # Unicode with a non-space low ASCII character \x05 in it
        pr['UnprintableUnicode'] = b'a\xc3\xa4\x05z1\xc3\xa9'.decode('UTF-8')
        io = BytesIO()
        pr.write(io)
        expected = '''ProblemType: Crash
Date: now!
Simple: bar
SimpleUTF8: 1äö2Φ3
SimpleUnicode: 1äö2Φ3
TwoLineUTF8:
 pi-π
 nu-η
TwoLineUnicode:
 pi-π
 nu-η
UnprintableUnicode: aä\x05z1é
WhiteSpace:
  foo   bar
 baz
   blip  
 
 afteremptyline
'''
        expected = expected.encode('UTF-8')
        self.assertEqual(io.getvalue(), expected)

    def test_load(self):
        '''load() with various formatting.'''

        pr = problem_report.ProblemReport()
        pr.load(BytesIO(b'''ProblemType: Crash
Date: now!
Simple: bar
WhiteSpace:
  foo   bar
 baz
   blip  
'''))
        self.assertEqual(pr['ProblemType'], 'Crash')
        self.assertEqual(pr['Date'], 'now!')
        self.assertEqual(pr['Simple'], 'bar')
        self.assertEqual(pr['WhiteSpace'], ' foo   bar\nbaz\n  blip  ')

        # test last field a bit more
        pr.load(BytesIO(b'''ProblemType: Crash
Date: now!
Simple: bar
WhiteSpace:
  foo   bar
 baz
   blip  
 
'''))
        self.assertEqual(pr['ProblemType'], 'Crash')
        self.assertEqual(pr['Date'], 'now!')
        self.assertEqual(pr['Simple'], 'bar')
        self.assertEqual(pr['WhiteSpace'], ' foo   bar\nbaz\n  blip  \n')

        # last field might not be \n terminated
        pr.load(BytesIO(b'''ProblemType: Crash
Date: now!
Simple: bar
WhiteSpace:
 foo
 bar'''))
        self.assertEqual(pr['ProblemType'], 'Crash')
        self.assertEqual(pr['Date'], 'now!')
        self.assertEqual(pr['Simple'], 'bar')
        self.assertEqual(pr['WhiteSpace'], 'foo\nbar')

        pr = problem_report.ProblemReport()
        pr.load(BytesIO(b'''ProblemType: Crash
WhiteSpace:
  foo   bar
 baz
 
   blip  
Last: foo
'''))
        self.assertEqual(pr['WhiteSpace'], ' foo   bar\nbaz\n\n  blip  ')
        self.assertEqual(pr['Last'], 'foo')

        pr.load(BytesIO(b'''ProblemType: Crash
WhiteSpace:
  foo   bar
 baz
   blip  
Last: foo
 
'''))
        self.assertEqual(pr['WhiteSpace'], ' foo   bar\nbaz\n  blip  ')
        self.assertEqual(pr['Last'], 'foo\n')

        # empty lines in values must have a leading space in coding
        invalid_spacing = BytesIO(b'''WhiteSpace:
 first

 second
''')
        pr = problem_report.ProblemReport()
        self.assertRaises(ValueError, pr.load, invalid_spacing)

        # test that load() cleans up properly
        pr.load(BytesIO(b'ProblemType: Crash'))
        self.assertEqual(list(pr.keys()), ['ProblemType'])

    def test_write_fileobj(self):
        '''writing a report with a pointer to a file-like object.'''

        tempbin = BytesIO(bin_data)
        tempasc = BytesIO(b'Hello World')

        pr = problem_report.ProblemReport(date='now!')
        pr['BinFile'] = (tempbin,)
        pr['AscFile'] = (tempasc, False)
        io = BytesIO()
        pr.write(io)
        io.seek(0)

        pr = problem_report.ProblemReport()
        pr.load(io)
        self.assertEqual(pr['BinFile'], tempbin.getvalue())
        self.assertEqual(pr['AscFile'], tempasc.getvalue().decode())

    def test_write_empty_fileobj(self):
        '''writing a report with a pointer to a file-like object with enforcing non-emptyness.'''

        tempbin = BytesIO(b'')
        tempasc = BytesIO(b'')

        pr = problem_report.ProblemReport(date='now!')
        pr['BinFile'] = (tempbin, True, None, True)
        io = BytesIO()
        self.assertRaises(IOError, pr.write, io)

        pr = problem_report.ProblemReport(date='now!')
        pr['AscFile'] = (tempasc, False, None, True)
        io = BytesIO()
        self.assertRaises(IOError, pr.write, io)

    def test_read_file(self):
        '''reading a report with binary data.'''

        bin_report = b'''ProblemType: Crash
Date: now!
File: base64
 H4sICAAAAAAC/0ZpbGUA
 c3RyhEIGBoYoRiYAM5XUCxAAAAA=
Foo: Bar
'''

        # test with reading everything
        pr = problem_report.ProblemReport()
        pr.load(BytesIO(bin_report))
        self.assertEqual(pr['File'], bin_data)
        self.assertEqual(pr.has_removed_fields(), False)

        # test with skipping binary data
        pr.load(BytesIO(bin_report), binary=False)
        self.assertEqual(pr['File'], '')
        self.assertEqual(pr.has_removed_fields(), True)

        # test with keeping compressed binary data
        pr.load(BytesIO(bin_report), binary='compressed')
        self.assertEqual(pr['Foo'], 'Bar')
        self.assertEqual(pr.has_removed_fields(), False)
        self.assertTrue(isinstance(pr['File'], problem_report.CompressedValue))
        self.assertEqual(len(pr['File']), len(bin_data))
        self.assertEqual(pr['File'].get_value(), bin_data)

    def test_read_file_legacy(self):
        '''reading a report with binary data in legacy format without gzip
        header.'''

        bin_report = b'''ProblemType: Crash
Date: now!
File: base64
 eJw=
 c3RyxIAMcBAFAG55BXk=
Foo: Bar
'''

        # test with reading everything
        pr = problem_report.ProblemReport()
        pr.load(BytesIO(bin_report))
        self.assertEqual(pr['File'], b'AB' * 10 + b'\0' * 10 + b'Z')
        self.assertEqual(pr.has_removed_fields(), False)

        # test with skipping binary data
        pr.load(BytesIO(bin_report), binary=False)
        self.assertEqual(pr['File'], '')
        self.assertEqual(pr.has_removed_fields(), True)

        # test with keeping CompressedValues
        pr.load(BytesIO(bin_report), binary='compressed')
        self.assertEqual(pr.has_removed_fields(), False)
        self.assertEqual(len(pr['File']), 31)
        self.assertEqual(pr['File'].get_value(), b'AB' * 10 + b'\0' * 10 + b'Z')
        io = BytesIO()
        pr['File'].write(io)
        io.seek(0)
        self.assertEqual(io.read(), b'AB' * 10 + b'\0' * 10 + b'Z')

    def test_iter(self):
        '''problem_report.ProblemReport iteration.'''

        pr = problem_report.ProblemReport()
        pr['foo'] = 'bar'

        keys = []
        for k in pr:
            keys.append(k)
        keys.sort()
        self.assertEqual(' '.join(keys), 'Date ProblemType foo')

        self.assertEqual(len([k for k in pr if k != 'foo']), 2)

    def test_modify(self):
        '''reading, modifying fields, and writing back.'''

        report = b'''ProblemType: Crash
Date: now!
Long:
 xxx
 .
 yyy
Short: Bar
File: base64
 H4sICAAAAAAC/0ZpbGUA
 c3RyxIAMcBAFAK/2p9MfAAAA
'''

        pr = problem_report.ProblemReport()
        pr.load(BytesIO(report))

        self.assertEqual(pr['Long'], 'xxx\n.\nyyy')

        # write back unmodified
        io = BytesIO()
        pr.write(io)
        self.assertEqual(io.getvalue(), report)

        pr['Short'] = 'aaa\nbbb'
        pr['Long'] = '123'
        io = BytesIO()
        pr.write(io)
        self.assertEqual(io.getvalue(),
                         b'''ProblemType: Crash
Date: now!
Long: 123
Short:
 aaa
 bbb
File: base64
 H4sICAAAAAAC/0ZpbGUA
 c3RyxIAMcBAFAK/2p9MfAAAA
''')

    def test_write_mime_text(self):
        '''write_mime() for text values.'''

        pr = problem_report.ProblemReport(date='now!')
        pr['Simple'] = 'bar'
        pr['SimpleUTF8'] = '1äö2Φ3'.encode('UTF-8')
        pr['SimpleUnicode'] = '1äö2Φ3'
        pr['TwoLineUnicode'] = 'pi-π\nnu-η\n'
        pr['TwoLineUTF8'] = 'pi-π\nnu-η\n'.encode('UTF-8')
        pr['SimpleLineEnd'] = 'bar\n'
        pr['TwoLine'] = 'first\nsecond\n'
        pr['InlineMargin'] = 'first\nsecond\nthird\nfourth\nfifth\n'
        pr['Multiline'] = ' foo   bar\nbaz\n  blip  \nline4\nline♥5!!\nłıµ€ ⅝\n'

        # still small enough for inline text
        pr['Largeline'] = 'A' * 999
        pr['LargeMultiline'] = 'A' * 120 + '\n' + 'B' * 90

        # too big for inline text, these become attachments
        pr['Hugeline'] = 'A' * 10000
        pr['HugeMultiline'] = 'A' * 900 + '\n' + 'B' * 900 + '\n' + 'C' * 900
        io = BytesIO()
        pr.write_mime(io)
        io.seek(0)

        msg = email.message_from_binary_file(io)
        parts = [p for p in msg.walk()]
        self.assertEqual(len(parts), 5)

        # first part is the multipart container
        self.assertTrue(parts[0].is_multipart())

        # second part should be an inline text/plain attachments with all short
        # fields
        self.assertTrue(not parts[1].is_multipart())
        self.assertEqual(parts[1].get_content_type(), 'text/plain')
        self.assertEqual(parts[1].get_content_charset(), 'utf-8')
        self.assertEqual(parts[1].get_filename(), None)
        expected = '''ProblemType: Crash
Date: now!
InlineMargin:
 first
 second
 third
 fourth
 fifth
LargeMultiline:
 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
 BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
Largeline: %s
Simple: bar
SimpleLineEnd: bar
SimpleUTF8: 1äö2Φ3
SimpleUnicode: 1äö2Φ3
TwoLine:
 first
 second
TwoLineUTF8:
 pi-π
 nu-η
TwoLineUnicode:
 pi-π
 nu-η
''' % pr['Largeline']
        expected = expected.encode('UTF-8')
        self.assertEqual(parts[1].get_payload(decode=True), expected)

        # third part should be the HugeMultiline: field as attachment
        self.assertTrue(not parts[2].is_multipart())
        self.assertEqual(parts[2].get_content_type(), 'text/plain')
        self.assertEqual(parts[2].get_content_charset(), 'utf-8')
        self.assertEqual(parts[2].get_filename(), 'HugeMultiline.txt')
        self.assertEqual(parts[2].get_payload(decode=True), pr['HugeMultiline'].encode())

        # fourth part should be the Hugeline: field as attachment
        self.assertTrue(not parts[3].is_multipart())
        self.assertEqual(parts[3].get_content_type(), 'text/plain')
        self.assertEqual(parts[3].get_content_charset(), 'utf-8')
        self.assertEqual(parts[3].get_filename(), 'Hugeline.txt')
        self.assertEqual(parts[3].get_payload(decode=True), pr['Hugeline'].encode())

        # fifth part should be the Multiline: field as attachment
        self.assertTrue(not parts[4].is_multipart())
        self.assertEqual(parts[4].get_content_type(), 'text/plain')
        self.assertEqual(parts[4].get_content_charset(), 'utf-8')
        self.assertEqual(parts[4].get_filename(), 'Multiline.txt')
        expected = ''' foo   bar
baz
  blip  
line4
line♥5!!
łıµ€ ⅝
'''
        expected = expected.encode('UTF-8')
        self.assertEqual(parts[4].get_payload(decode=True), expected)

    def test_write_mime_extra_headers(self):
        '''write_mime() with extra headers.'''

        pr = problem_report.ProblemReport(date='now!')
        pr['Simple'] = 'bar'
        pr['TwoLine'] = 'first\nsecond\n'
        io = BytesIO()
        pr.write_mime(io, extra_headers={'Greeting': 'hello world',
                                         'Foo': 'Bar'})
        io.seek(0)

        msg = email.message_from_binary_file(io)
        self.assertEqual(msg['Greeting'], 'hello world')
        self.assertEqual(msg['Foo'], 'Bar')
        parts = [p for p in msg.walk()]
        self.assertEqual(len(parts), 2)

        # first part is the multipart container
        self.assertTrue(parts[0].is_multipart())

        # second part should be an inline text/plain attachments with all short
        # fields
        self.assertTrue(not parts[1].is_multipart())
        self.assertEqual(parts[1].get_content_type(), 'text/plain')
        self.assertTrue(b'Simple: bar' in parts[1].get_payload(decode=True))

    def test_write_mime_order(self):
        '''write_mime() with keys ordered.'''

        pr = problem_report.ProblemReport(date='now!')
        pr['SecondText'] = 'What'
        pr['FirstText'] = 'Who'
        pr['FourthText'] = 'Today'
        pr['ThirdText'] = "I Don't Know"
        io = BytesIO()
        pr.write_mime(io, priority_fields=['FirstText', 'SecondText',
                                           'ThirdText', 'Unknown', 'FourthText'])
        io.seek(0)

        msg = email.message_from_binary_file(io)
        parts = [p for p in msg.walk()]
        self.assertEqual(len(parts), 2)

        # first part is the multipart container
        self.assertTrue(parts[0].is_multipart())

        # second part should be an inline text/plain attachments with all short
        # fields
        self.assertTrue(not parts[1].is_multipart())
        self.assertEqual(parts[1].get_content_type(), 'text/plain')
        self.assertEqual(parts[1].get_content_charset(), 'utf-8')
        self.assertEqual(parts[1].get_filename(), None)
        self.assertEqual(parts[1].get_payload(decode=True), b'''FirstText: Who
SecondText: What
ThirdText: I Don't Know
FourthText: Today
ProblemType: Crash
Date: now!
''')

    def test_updating(self):
        '''new_keys() and write() with only_new=True.'''

        pr = problem_report.ProblemReport()
        self.assertEqual(pr.new_keys(), set(['ProblemType', 'Date']))
        pr.load(BytesIO(b'''ProblemType: Crash
Date: now!
Foo: bar
Baz: blob
'''))

        self.assertEqual(pr.new_keys(), set())

        pr['Foo'] = 'changed'
        pr['NewKey'] = 'new new'
        self.assertEqual(pr.new_keys(), set(['NewKey']))

        out = BytesIO()
        pr.write(out, only_new=True)
        self.assertEqual(out.getvalue(), b'NewKey: new new\n')

    def test_import_dict(self):
        '''importing a dictionary with update().'''

        pr = problem_report.ProblemReport()
        pr['oldtext'] = 'Hello world'
        pr['oldbin'] = bin_data
        pr['overwrite'] = 'I am crap'

        d = {}
        d['newtext'] = 'Goodbye world'
        d['newbin'] = '11\000\001\002\xFFZZ'
        d['overwrite'] = 'I am good'

        pr.update(d)
        self.assertEqual(pr['oldtext'], 'Hello world')
        self.assertEqual(pr['oldbin'], bin_data)
        self.assertEqual(pr['newtext'], 'Goodbye world')
        self.assertEqual(pr['newbin'], '11\000\001\002\xFFZZ')
        self.assertEqual(pr['overwrite'], 'I am good')

    def test_load_key_filter(self):
        '''load a report with filtering keys.'''

        io = BytesIO(b'''ProblemType: Crash
DataNo: nonono
GoodFile: base64
 H4sICAAAAAAC/0FmaWxlAA==
 c3RyhEIGBoYoRiYAM5XUCxAAAAA=
DataYes: yesyes
BadFile: base64
 H4sICAAAAAAC/0ZpbGUA
 S8vPZ0hKLAIACq50HgcAAAA=
''')
        pr = problem_report.ProblemReport()
        pr.load(io, key_filter=['DataYes', 'GoodFile'])
        self.assertEqual(pr['DataYes'], 'yesyes')
        self.assertEqual(pr['GoodFile'], bin_data)
        self.assertEqual(sorted(pr.keys()), ['DataYes', 'GoodFile'])
