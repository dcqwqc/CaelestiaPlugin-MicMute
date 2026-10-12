import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / 'scripts' / 'mic-mute.py'
spec = importlib.util.spec_from_file_location('micmute', SRC)
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)


class Result:
    returncode = 0
    def __init__(self, stdout):
        self.stdout = stdout


class MicrophoneSourceTests(unittest.TestCase):
    def test_default_quest_monitor_is_included(self):
        sources = '1\thardware_mic\n2\tqsw_quest_microphone.monitor\n3\tspeaker.monitor\n'
        with patch.object(mm, 'run', side_effect=[Result(sources), Result('qsw_quest_microphone.monitor\n')]):
            self.assertEqual(mm.input_sources(), ['hardware_mic', 'qsw_quest_microphone.monitor'])

    def test_quest_stays_in_sync_after_default_changes(self):
        sources = '1\tphysical\n2\tqsw_quest_microphone.monitor\n3\tspeaker.monitor\n'
        with patch.object(mm, 'run', side_effect=[Result(sources), Result('physical\n')]):
            self.assertEqual(mm.input_sources(), ['physical', 'qsw_quest_microphone.monitor'])

    def test_other_output_monitors_are_not_muted(self):
        with patch.object(mm, 'run', side_effect=[Result('1\tphysical\n2\tspeaker.monitor\n'), Result('physical\n')]):
            self.assertEqual(mm.input_sources(), ['physical'])


if __name__ == '__main__':
    unittest.main()
