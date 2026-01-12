Modify the listen_app.py UI in the following ways:

- Retain the status line that displays "Recording" and "Processing"
- Underneath the status line, add a multi-line text box. Accumulate the transcribed text here. Allow the user to edit the transcribed text.
- Move the "Record" button to the left. Add an "Improve" button. Add a "Finish" button
- The "Record" button behaves as before. Clicking "Record" will record audio and transcribe to the multi-line text box.
- The new "Improve" button will send the text from the multi-line text box to the improve command standard input using the subprocess module. After the text has been improved by the improve command, replace the text in the multi-line text box with the improved text from the standout out of the improve command.
- The new "Finish" button, will print the text from the multi-line entry box to the standard out and close the UI.
