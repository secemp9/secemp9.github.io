"""Keep draft HTML out of production, including custom output paths."""

from pelican import signals


def suppress_draft_output(content):
    # Check the current build's settings: a process can build production and
    # development in succession while the signal receiver remains registered.
    if content.settings.get('EXCLUDE_DRAFTS') and content.status == 'draft':
        content.override_save_as = ''


def register():
    signals.content_object_init.connect(suppress_draft_output)
