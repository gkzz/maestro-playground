"""Build screenshot summaries from Maestro's assertion evidence."""
import json
import math


class ScreenshotReport:
    def __init__(self, downloads, output, locale, platforms):
        self.downloads = downloads
        self.output = output
        self.locale = locale
        self.platforms = platforms
        self.unavailable = []

    def result_root(self, platform):
        named = self.downloads / f'maestro-{platform}-unicode'
        if named.is_dir():
            return named
        if any(self.downloads.glob('maestro-*-unicode')):
            return named
        # gh extracts a single artifact directly into the download directory.
        states = {os for os in ('android', 'ios') if any(self.downloads.rglob(
            f'{os}-unicode-field-{self.locale}-baseline-state.txt'))}
        if states == {platform}:
            return self.downloads
        return named

    @staticmethod
    def artifact(root, relative):
        if not isinstance(relative, str):
            raise ValueError('Missing assertion image path')
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
            raise ValueError('Assertion image missing or outside result directory')
        return candidate

    def build(self):
        self.output.mkdir(parents=True, exist_ok=True)
        sections = []
        for platform in self.platforms:
            root = self.result_root(platform)
            section = [f'### {platform} / {self.locale}', '']
            try:
                states = list(root.rglob(f'{platform}-unicode-field-{self.locale}-baseline-state.txt'))
                state = states[0].read_text().strip() if len(states) == 1 else None
                if state not in ('present', 'absent'):
                    raise ValueError('Baseline availability unknown')
                files = list(root.rglob('commands.json'))
                if len(files) != 1:
                    raise ValueError('Maestro commands.json missing or ambiguous')
                commands = json.loads(files[0].read_text())
                # Match the leaf command only, never its runFlow/retry container.
                assertions = [entry for entry in commands
                              if 'assertScreenshotCommand' in entry['command']]
                if state == 'absent':
                    if any(entry['metadata'].get('status') != 'SKIPPED' for entry in assertions):
                        raise ValueError('Assertion executed despite absent baseline')
                    section += ['Not compared: no baseline for this OS/locale.', '']
                else:
                    if not assertions:
                        raise ValueError('Maestro assertion result unavailable')
                    section += ['| Assertion | Result | Match | Threshold | Images |',
                                '| --- | --- | --- | --- | --- |']
                    for index, entry in enumerate(assertions, 1):
                        metadata = entry['metadata']
                        status = metadata.get('status')
                        if status not in ('COMPLETED', 'FAILED'):
                            raise ValueError(f'Assertion {index}: result unavailable')
                        comparison = metadata.get('screenshotComparison', {})
                        percentage = comparison.get('matchPercentage')
                        threshold = comparison.get('thresholdPercentage')
                        def valid_percentage(value):
                            return (type(value) in (int, float) and math.isfinite(value)
                                    and 0 <= value <= 100)
                        if not valid_percentage(threshold):
                            raise ValueError(f'Assertion {index}: threshold unavailable')
                        if comparison.get('sizeMismatch') is True and status == 'FAILED' and percentage is None:
                            match = 'N/A (image size mismatch)'
                        elif valid_percentage(percentage):
                            match = str(percentage).removesuffix('.0') + '%'
                        else:
                            raise ValueError(f'Assertion {index}: measured match percentage unavailable')
                        current = self.artifact(files[0].parent, comparison.get('actualPath'))
                        if current.suffix.lower() != '.png':
                            raise ValueError(f'Assertion {index}: actual image is not PNG')
                        artifacts = metadata.get('artifacts', [])
                        if not any(item.get('type') == 'SCREENSHOT' and
                                   item.get('path') == comparison.get('actualPath') for item in artifacts):
                            raise ValueError(f'Assertion {index}: actual image not registered')
                        dest = self.output / f'{platform}-assertion-{index}-actual.png'
                        dest.write_bytes(current.read_bytes())
                        images = [f'Actual: `{dest.name}`']
                        for item in artifacts:
                            if item.get('type') == 'SCREENSHOT_DIFF':
                                diff = self.artifact(files[0].parent, item.get('path'))
                                dest = self.output / f'{platform}-assertion-{index}-diff.png'
                                dest.write_bytes(diff.read_bytes())
                                images.append(f'Diff: `{dest.name}`')
                        section.append(f'| {index} | {status} | {match} | {threshold:g}% | '
                                       + '<br>'.join(images) + ' |')
                    section += ['', '[Download assertion images](@@)', '']
            except (ValueError, OSError, TypeError, AttributeError, KeyError) as error:
                self.unavailable.append(f'{platform}: {error}')
                section += [f'Assertion result unavailable: {error}. See the source job logs.', '']
            sections.append('\n'.join(section))
        return '\n'.join(sections)
