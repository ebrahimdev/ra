// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { CitationService } from './citationService';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// Use the console to output diagnostic information (console.log) and errors (console.error)
	// This line of code will only be executed once when your extension is activated
	console.log('Congratulations, your extension "quill" is now active!');
	console.log('Extension context:', context.extensionPath);
	console.log('Extension version:', context.extension.packageJSON.version);

	// The command has been defined in the package.json file
	// Now provide the implementation of the command with registerCommand
	// The commandId parameter must match the command field in package.json
	const helloWorldDisposable = vscode.commands.registerCommand('quill.helloWorld', () => {
		// The code you place here will be executed every time your command is executed
		// Display a message box to the user
		vscode.window.showInformationMessage('Hello World from quill!');
	});

	// Register the suggest citation command
	const suggestCitationDisposable = vscode.commands.registerCommand('quill.suggestCitation', async () => {
		console.log('quill.suggestCitation command triggered');

		const editor = vscode.window.activeTextEditor;
		if (!editor) {
			console.error('No active editor found');
			vscode.window.showErrorMessage('No active editor found');
			return;
		}

		console.log('Active editor found:', editor.document.fileName);
		console.log('Document language:', editor.document.languageId);

		try {
			// Extract text from the current editor
			const text = CitationService.extractTextFromEditor(editor);
			if (!text.trim()) {
				vscode.window.showErrorMessage('No text found to analyze');
				return;
			}

			// Show progress indicator
			await vscode.window.withProgress({
				location: vscode.ProgressLocation.Notification,
				title: 'Analyzing text for citation suggestions...',
				cancellable: false
			}, async () => {
				// Send text to backend for citation suggestion
				const response = await CitationService.suggestCitation(text);

				if (!response) {
					vscode.window.showErrorMessage('Failed to get citation suggestion from server');
					return;
				}

				if (!response.match || !response.paper) {
					vscode.window.showInformationMessage('No relevant citation found for the selected text');
					return;
				}

				// Show citation suggestion to user
				const shouldInsert = await CitationService.showCitationSuggestion(response.paper);

				if (shouldInsert) {
					// Insert citation in the current file
					CitationService.insertCitation(editor, response.paper.citation_key);

					// Append bibtex entry to .bib file
					const bibtexAdded = await CitationService.appendBibtexEntry(response.paper.bibtex);

					if (bibtexAdded) {
						vscode.window.showInformationMessage(`Citation inserted and bibliography updated!`);
					} else {
						vscode.window.showWarningMessage(`Citation inserted but failed to update bibliography file`);
					}
				}
			});
		} catch (error) {
			console.error('Error in suggestCitation command:', error);
			console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace available');
			vscode.window.showErrorMessage('An error occurred while suggesting citations');
		}
	});

	context.subscriptions.push(helloWorldDisposable, suggestCitationDisposable);
}

// This method is called when your extension is deactivated
export function deactivate() {
	console.log('Quill extension is being deactivated');
}
