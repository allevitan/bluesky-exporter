import itertools
import shutil
from collections import Counter
from pathlib import Path
import re
import unicodedata

from PyQt5.QtWidgets import QMessageBox
from qtpy.QtWidgets import QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QToolButton, QFileDialog, QCheckBox, \
    QComboBox
from qtpy.QtWidgets import QApplication, QSizePolicy
from qtpy.QtCore import Qt
from databroker import Broker
from qtpy.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QGroupBox
from qtmodern import styles

from xicam.gui.bluesky.databroker_catalog_plugin import SearchingCatalogController
from xicam.gui.widgets.metadataview import MetadataWidget

__all__ = ['main']

# Consistently styling the pyqtgraph parametertrees across styles with reasonable colors
pyqtgraph_parametertree_fixes = """
QTreeView::item:has-children {
    background: palette(dark);
    color: palette(light);
}
"""


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


class ExportSettings(QGroupBox):
    def __init__(self, *args, **kwargs):
        super(ExportSettings, self).__init__('Export Settings', *args, **kwargs)
        self.setLayout(form_layout := QFormLayout())

        self.export_directory_path = QLineEdit()
        self.export_directory_button = QToolButton()
        self.export_directory_button.setText('...')
        self.munge_filenames = QCheckBox('Use sample name as filename')
        self.munge_filenames.setChecked(True)
        self.convert = QCheckBox('Convert file format')
        self.convert.setChecked(True)
        self.new_format = QComboBox()

        export_directory_layout = QHBoxLayout()
        export_directory_layout.addWidget(self.export_directory_path)
        export_directory_layout.addWidget(self.export_directory_button)

        form_layout.addRow('Export Directory:', export_directory_layout)
        form_layout.addWidget(self.munge_filenames)
        # form_layout.addWidget(self.convert)

        self.export_directory_button.clicked.connect(self.choose_directory)

    def choose_directory(self):
        path = str(QFileDialog.getExistingDirectory(self, "Select Export Directory"))
        if path:
            self.export_directory_path.setText(path)


class Exporter(QWidget):
    def __init__(self, broker, *args, **kwargs):
        super(Exporter, self).__init__()

        self.setLayout(hlayout := QHBoxLayout())
        hlayout.addLayout(vlayout := QVBoxLayout())

        self.export_settings_widget = ExportSettings()
        self.browser_widget = SearchingCatalogController(broker)
        self.metadata_widget = MetadataWidget()

        vlayout.addWidget(self.export_settings_widget)
        vlayout.addWidget(self.browser_widget)
        hlayout.addWidget(self.metadata_widget)

        self.browser_widget.sigOpen.connect(self.export)
        self.browser_widget.sigPreview.connect(self.metadata_widget.show_catalog)

        self.browser_widget.open_button.setText('Export')

    def export(self, catalog):
        export_dir = self.export_settings_widget.export_directory_path.text()

        if not export_dir:
            QMessageBox.information(self, 'Cannot export', 'Select an export directory.')
            return

        resource_counter = itertools.count()

        for name, doc in catalog.canonical(fill='no'):
            if name == 'start':
                sample_name = slugify(doc['sample_name'])

            elif name == 'resource':
                src_path = Path(doc['root']) / Path(doc['resource_path'])
                dest_path = (Path(export_dir) / Path(f"{sample_name}_{next(resource_counter)}")).with_suffix(Path(doc['resource_path']).suffix)
                shutil.copy2(src_path, dest_path)


class ExporterWindow(QMainWindow):
    def __init__(self, broker, *args, **kwargs):
        super(ExporterWindow, self).__init__(*args, **kwargs)
        self.exporter = Exporter(broker)
        self.setCentralWidget(self.exporter)


def main():
    import sys
    if len(sys.argv) > 1:
        broker_name = sys.argv[1]
    else:
        broker_name = 'local'

    db = Broker.named(broker_name).v2

    app = QApplication([])
    styles.dark(app)
    app.setStyleSheet(pyqtgraph_parametertree_fixes)

    w = ExporterWindow(db)

    w.show()

    exit(app.exec_())


if __name__ == '__main__':
    main()