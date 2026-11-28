"""Build screenshot summaries from Maestro results."""
import json


class ScreenshotReport:
    def __init__(self, downloads, output, locale, platforms):
        self.downloads = downloads
        self.output = output
        self.locale = locale
        self.platforms = platforms
        self.unavailable = []

    def assertion(self, platform, result_root=None):
        """Return the last executed Maestro screenshot assertion and its artifacts."""
        if result_root is None:
            result_root = self.downloads / f'maestro-{platform}-unicode'
            if not result_root.is_dir():
                if any(self.downloads.glob('maestro-*-unicode')):
                    return None, []
                platforms = {candidate for candidate in ('android', 'ios')
                             if any(self.downloads.rglob(
                                 f'{candidate}-unicode-field-{self.locale}.png'))}
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
        artifacts = {path.name: path for path in self.downloads.glob('maestro-*-unicode*')
                     if path.is_dir()}
        for platform in self.platforms:
            prefix = f'maestro-{platform}-unicode'
            suffix = f'-{self.locale}'
            versioned = [(name[len(prefix) + 1:-len(suffix)], path)
                         for name, path in sorted(artifacts.items())
                         if name.startswith(prefix + '-') and name.endswith(suffix)]
            if versioned:
                sections.extend(self.section(platform, path, version=version)
                                for version, path in versioned)
            else:
                sections.append(self.section(platform, self.downloads))
        return '\n'.join(sections)

    def section(self, platform, result_root, *, version=None):
        stem = f'{platform}-unicode-field-{self.locale}'
        matches = list(result_root.rglob(f'{stem}.png'))
        label = f'{platform} {version}' if version else platform
        output_stem = f'{platform}-{version}-unicode-field-{self.locale}' if version else stem
        section = [f'### {label} / {self.locale}', '']
        if not matches:
            self.unavailable.append(f'{label}: capture unavailable')
            return '\n'.join(section + ['No capture available. See the source job logs.', ''])
        if len(matches) != 1:
            raise ValueError(f'Ambiguous screenshot: {stem}')
        current = self.output / f'{output_stem}-current.png'
        current.write_bytes(matches[0].read_bytes())
        states = list(result_root.rglob(f'{stem}-baseline-state.txt'))
        baselines = list(result_root.rglob(f'{stem}-baseline.png'))
        state = states[0].read_text().strip() if len(states) == 1 else None
        if state == 'present' and len(baselines) == 1:
            baseline = baselines[0]
            reference = self.output / f'{output_stem}-baseline.png'
            reference.write_bytes(baseline.read_bytes())
            try:
                status, artifacts = self.assertion(label, result_root if version else None)
            except (ValueError, OSError, TypeError, AttributeError):
                status, artifacts = None, []
            if status not in ('COMPLETED', 'FAILED'):
                self.unavailable.append(f'{label}: Maestro assertion result unavailable')
            section += [f'Maestro assertScreenshot: {status or "result unavailable"}', '']
            cells = [f'![baseline](@@/{reference.name})', f'![current](@@/{current.name})']
            headings = ['Baseline', 'Current']
            diffs = [path for path in artifacts if path.suffix.lower() == '.png'
                     and 'diff' in path.name.lower()]
            if diffs:
                diff = self.output / f'{output_stem}-diff.png'
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
            self.unavailable.append(f'{label}: baseline provenance unavailable')
            section += ['Baseline provenance unavailable. See the source job logs.', '',
                        f'![current](@@/{current.name})', '']
        screens = list(result_root.rglob(f'{platform}-unicode-input-{self.locale}.png'))
        if len(screens) == 1:
            full = self.output / (f'{platform}-{version}-unicode-input-{self.locale}.png'
                                  if version else screens[0].name)
            full.write_bytes(screens[0].read_bytes())
            section += ['<details><summary>Full screen</summary>', '',
                        f'<img src="@@/{full.name}" alt="{platform} input screen" width="320">',
                        '', '</details>', '']
        return '\n'.join(section)
