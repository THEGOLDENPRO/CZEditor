from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy, QMainWindow
from PySide6.QtGui import QPainter

from czeditor.base_ui import (QRedButton, QRedDecimalSpinBox, QRedFrame,
                              QRedSpinBox, QRedTextBox, QRedTextEntry,
                              QRedExpandableButton, QRedComboBox)


class IntPropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QHBoxLayout()
        self.spinbox = QRedSpinBox(self, self.updateproperty)
        self.spinbox.setValue(self.theproperty._val)
        self.widgets.addWidget(self.spinbox)
        self.setLayout(self.widgets)
        self.setStyleSheet("border-width:0px;")

    def updateproperty(self, value):
        self.theproperty._val = value
        self.windowObject.updateviewport()

    def updateself(self):
        self.spinbox.setValue(self.theproperty._val)


class StringPropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QHBoxLayout()
        self.textbox = QRedTextBox(self)
        self.textbox.textChanged.connect(self.updateproperty)
        self.textbox.setPlainText(self.theproperty._val)
        # self.setFixedHeight(self.textbox.sizeHint().height())
        # self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.widgets.addWidget(self.textbox)
        self.setLayout(self.widgets)
        # self.setStyleSheet("border-image:url(editor/Square Frame.png) 2; border-width:2;")
        self.setStyleSheet("border-width:0px;")

    def updateproperty(self):
        self.theproperty._val = self.textbox.toPlainText()
        self.windowObject.updateviewport()

    def updateself(self):
        self.textbox.setPlainText(self.theproperty._val)


class OpenWindowButtonPropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.the_property = property
        self.window_:QMainWindow = self.the_property.window(property, windowObject)

        self.widgets = QHBoxLayout()

        self.button = QRedButton(self, self.the_property.btn_name, self.open_window)
        self.widgets.addWidget(self.button)

        self.setLayout(self.widgets)

        self.setStyleSheet("border-bottom-width:0px;")

    def open_window(self):
        self.window_.show()


class LineStringPropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QHBoxLayout()
        self.textbox = QRedTextEntry(self)
        self.textbox.textChanged.connect(self.updateproperty)
        self.textbox.setText(self.theproperty._val)
        # self.setFixedHeight(self.textbox.sizeHint().height())
        # self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.widgets.addWidget(self.textbox)
        self.setLayout(self.widgets)
        # self.setStyleSheet("border-image:url(editor/Square Frame.png) 2; border-width:2;")
        self.setStyleSheet("border-width:0px;")

    def updateproperty(self):
        self.theproperty._val = self.textbox.text()
        self.windowObject.updateviewport()

    def updateself(self):
        self.textbox.setText(self.theproperty._val)


class FilePropertyWidget(QRedFrame):
    def __init__(self, property, filetypes, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.filetypes = filetypes
        self.widgets = QVBoxLayout()
        self.textbox = QRedTextBox(self)
        self.textbox.textChanged.connect(self.updateproperty)
        self.textbox.setPlainText(self.theproperty._val)
        self.button = QRedButton(self, "Browse...", self.browse)

        # self.setFixedHeight(self.textbox.sizeHint().height())
        # self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.widgets.addWidget(self.textbox)
        self.widgets.addWidget(self.button)
        self.setLayout(self.widgets)
        # self.setStyleSheet("border-image:url(editor/Square Frame.png) 2; border-width:2;")
        self.setStyleSheet("border-width:0px;")

    def updateproperty(self):
        self.theproperty._val = self.textbox.toPlainText()
        self.windowObject.updateviewport()

    def updateself(self):
        self.textbox.setPlainText(self.theproperty._val)

    def browse(self):
        self.textbox.setPlainText(QFileDialog.getOpenFileUrl(
            self, "Open File", filter=self.filetypes)[0].path()[1:])
        # ,options=QFileDialog.Option.DontUseNativeDialog


class SizePropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QVBoxLayout()

        self.baseWidthLabel = QLabel(self)
        self.baseWidthLabel.setText(
            "Base Width\n"+str(self.theproperty._basewidth))
        self.widgets.addWidget(self.baseWidthLabel)

        self.widthSpinBox = QRedSpinBox(self, self.updateproperty)
        self.widgets.addWidget(self.widthSpinBox)

        self.relativeWidthSpinBox = QRedDecimalSpinBox(
            self, self.updaterelativeproperty)
        self.relativeWidthSpinBox.setSuffix("%")
        self.widgets.addWidget(self.relativeWidthSpinBox)

        self.baseHeightLabel = QLabel(self)
        self.baseHeightLabel.setText(
            "Base Height\n"+str(self.theproperty._baseheight))
        self.widgets.addWidget(self.baseHeightLabel)

        self.heightSpinBox = QRedSpinBox(self, self.updateproperty)
        self.widgets.addWidget(self.heightSpinBox)

        self.relativeHeightSpinBox = QRedDecimalSpinBox(
            self, self.updaterelativeproperty)
        self.relativeHeightSpinBox.setSuffix("%")
        self.widgets.addWidget(self.relativeHeightSpinBox)

        self.widthSpinBox.setValueBypass(self.theproperty._width)
        self.heightSpinBox.setValueBypass(self.theproperty._height)
        self.relativeWidthSpinBox.setValueBypass(
            self.theproperty._relativewidth*100)
        self.relativeHeightSpinBox.setValueBypass(
            self.theproperty._relativeheight*100)

        self.setStyleSheet(
            "border-image:url(editor:Square Frame.png) 2; border-width:2;")
        self.setLayout(self.widgets)

    def updateproperty(self, value):
        self.theproperty.set(
            (self.widthSpinBox.value(), self.heightSpinBox.value()))
        self.relativeWidthSpinBox.setValueBypass(
            self.theproperty._relativewidth*100)
        self.relativeHeightSpinBox.setValueBypass(
            self.theproperty._relativeheight*100)
        self.windowObject.updateviewport()

    def updaterelativeproperty(self, value):
        self.theproperty.setrelative(
            (self.relativeWidthSpinBox.value()/100, self.relativeHeightSpinBox.value()/100))
        self.widthSpinBox.setValueBypass(self.theproperty._width)
        self.heightSpinBox.setValueBypass(self.theproperty._height)
        self.windowObject.updateviewport()

    def updateself(self):
        self.baseWidthLabel.setText(
            "Base Width\n"+str(self.theproperty._basewidth))
        self.baseHeightLabel.setText(
            "Base Height\n"+str(self.theproperty._baseheight))
        self.widthSpinBox.setValue(self.theproperty._width)
        self.heightSpinBox.setValue(self.theproperty._height)
        self.relativeWidthSpinBox.setValue(self.theproperty._relativewidth*100)
        self.relativeHeightSpinBox.setValue(
            self.theproperty._relativeheight*100)


class FloatPropertyWidget(QRedFrame):

    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QHBoxLayout()
        self.spinbox = QRedDecimalSpinBox(self, self.updateproperty)
        self.spinbox.setValue(self.theproperty(
            self.windowObject.playbackframe))
        self.animationModeButton = QRedExpandableButton(
            self, "A", self.enterAnimationMode)
        self.animationModeButton.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.widgets.addWidget(self.spinbox)
        self.widgets.addWidget(self.animationModeButton)
        self.setLayout(self.widgets)
        self.setStyleSheet("border-width:0px;")
        self.windowObject.connectToEvent("FrameUpdate", self.updateself)

    def updateproperty(self, value):
        self.theproperty._val = value
        self.windowObject.updateviewport()

    def updateself(self):
        self.spinbox.onchange = self.lock  # Smart!
        self.spinbox.setValue(self.theproperty(
            self.windowObject.playbackframe))
        self.update()

    def enterAnimationMode(self):
        self.windowObject.enterAnimationMode(self.theproperty)

    def lock(self, value):
        self.spinbox.onchange = self.updateproperty

    def disconnectNotify(self, signal) -> None:
        self.windowObject.disconnectFromEvent("FrameUpdate", self.updateself)
        return super().disconnectNotify(signal)


class SelectablePropertyWidget(QRedFrame):
    def __init__(self, property, windowObject):
        super().__init__(None)
        self.windowObject = windowObject
        self.theproperty = property
        self.widgets = QHBoxLayout()
        self.combobox = QRedComboBox(
            self.widgets, self.theproperty._selectable.names)
        self.combobox.setCurrentIndex(self.theproperty._selectable.index)
        self.combobox.onchange = self.updateproperty

    def updateProperty(self, name, index):
        self.theproperty._selectable.index = index
        self.windowObject.updateviewport()

    def updateself(self):
        self.combobox.onchange = self.lock
        self.combobox.setCurrentIndex(self.theproperty._selectable.index)

    def lock(self, name, index):
        self.combobox.onchange = self.updateProperty
