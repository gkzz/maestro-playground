"""Build screenshot summaries from Maestro results."""
import json


class ScreenshotReport:
    def __init__(self, downloads, output, locale, platforms):
        self.downloads = downloads
        self.output = output
        self.locale = locale
        self.platforms = platforms
        self.unavailable = []

    def assertion(self, platform):
        """Return the last executed Maestro screenshot assertion and its artifacts."""
        result_root = self.downloads / f'maestro-{platform}-unicode'
        if not result_root.is_dir():
            # gh extracts a single artifact directly into the download directory.
            # Only accept that layout when captures identify this platform alone.
            if any(self.downloads.glob('maestro-*-unicode')):
                return None, []
            platforms = {os for os in ('android', 'ios')
                         if any(self.downloads.rglob(f'{os}-unicode-field-{self.locale}.png'))}
            if platforms != {platform}:
                return None, []
            result_root = self.downloads
        files = list(result_root.rglob('commands.json'))
        if len(files) > 1:
            raise ValueError(f'Ambiguous Maestro results: {platform}')
        if not files:
            return None, []
        commands = json.loads(files[0].read_text())
        matches = [entry for entry in commands
                   if 'assertScreenshot' in json.dumps(entry.get('command', {}))]
        if not matches:
            return None, []
        result = matches[-1]
        metadata = result.get('metadata', {})
        artifacts = []
        for item in metadata.get('artifacts', []):
            path = item.get('path')
            if path:
                candidate = (files[0].parent / path).resolve()
                if candidate.is_relative_to(files[0].parent.resolve()) and candidate.is_file():
                    artifacts.append(candidate)
        return metadata.get('status'), artifacts

    def build(self):
        self.output.mkdir(parents=True, exist_ok=True)
        sections = []
        for platform in self.platforms:
            stem = f'{platform}-unicode-field-{self.locale}'
            matches = list(self.downloads.rglob(f'{stem}.png'))
            section = [f'### {platform} / {self.locale}', '']
            if not matches:
                self.unavailable.append(f'{platform}: capture unavailable')
                sections.append('\n'.join(section + ['No capture available. See the source job logs.', '']))
                continue
            if len(matches) != 1:
                raise ValueError(f'Ambiguous screenshot: {stem}')
            current = self.output / f'{stem}-current.png'
            current.write_bytes(matches[0].read_bytes())
            states = list(self.downloads.rglob(f'{stem}-baseline-state.txt'))
            baselines = list(self.downloads.rglob(f'{stem}-baseline.png'))
            state = states[0].read_text().strip() if len(states) == 1 else None
            if state == 'present' and len(baselines) == 1:
                baseline = baselines[0]
                reference = self.output / f'{stem}-baseline.png'
                reference.write_bytes(baseline.read_bytes())
                try:
                    status, artifacts = self.assertion(platform)
                except (ValueError, OSError, TypeError, AttributeError):
                    status, artifacts = None, []
                if status not in ('COMPLETED', 'FAILED'):
                    self.unavailable.append(f'{platform}: Maestro assertion result unavailable')
                section += [f'Maestro assertScreenshot: {status or "result unavailable"}', '']
                cells = [f'![baseline](@@/{reference.name})', f'![current](@@/{current.name})']
                headings = ['Baseline', 'Current']
                diffs = [path for path in artifacts if path.suffix.lower() == '.png'
                         and 'diff' in path.name.lower()]
                if diffs:
                    diff = self.output / f'{stem}-diff.png'
                    diff.write_bytes(diffs[-1].read_bytes())
                    headings.append('Diff')
                    cells.append(f'![diff](@@/{diff.name})')
                section += ['| ' + ' | '.join(headings) + ' |',
                            '| ' + ' | '.join('---' for _ in headings) + ' |',
                            '| ' + ' | '.join(cells) + ' |', '']
            elif state == 'absent' and not baselines:
                section += ['Not compared: no baseline for this OS/locale.', '',
                            f'![current](@@/{current.name})', '']
            else:
                self.unavailable.append(f'{platform}: baseline provenance unavailable')
                section += ['Baseline provenance unavailable. See the source job logs.', '',
                            f'![current](@@/{current.name})', '']
            screens = list(self.downloads.rglob(f'{platform}-unicode-input-{self.locale}.png'))
            if len(screens) == 1:
                full = self.output / screens[0].name
                full.write_bytes(screens[0].read_bytes())
                section += ['<details><summary>Full screen</summary>', '',
                            f'<img src="@@/{full.name}" alt="{platform} input screen" width="320">',
                            '', '</details>', '']
            sections.append('\n'.join(section))
        return '\n'.join(sections)
