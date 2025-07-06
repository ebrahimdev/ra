// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { CitationService } from './citationService';
import { logInfo, logError } from './logger';


// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// Use the console to output diagnostic information (console.log) and errors (console.error)
	// This line of code will only be executed once when your extension is activated
	logInfo('🎉 Quill extension is now active!');
	logInfo('Extension context: ' + context.extensionPath);
	logInfo('Extension version: ' + context.extension.packageJSON.version);
	logInfo('Activation time: ' + new Date().toISOString());

	CitationService.initializeProactiveSuggestions(context);

	const suggestCitationDisposable = vscode.commands.registerCommand('quill.suggestCitation', async () => {
		const editor = vscode.window.activeTextEditor;
		if (!editor) {
			vscode.window.showErrorMessage('No active editor found');
			return;
		}

		try {
			const position = editor.selection.active;
			await vscode.window.withProgress({
				location: vscode.ProgressLocation.Notification,
				title: 'Analyzing text for citation suggestions...',
				cancellable: false
			}, async () => {
				await CitationService.processCitationSuggestionAtPosition(editor.document, position, editor);
			});
		} catch (error) {
			logError('Error in suggestCitation command: ' + error);
			logError('Error stack: ' + (error instanceof Error ? error.stack : 'No stack trace available'));
			vscode.window.showErrorMessage('An error occurred while suggesting citations');
		}
	});

	const clearTrackingDisposable = vscode.commands.registerCommand('quill.clearCitationTracking', () => {
		CitationService.clearInsertedCitationsTracking();
	});

	context.subscriptions.push(suggestCitationDisposable, clearTrackingDisposable);
}

export function deactivate() {
	logInfo('Quill extension is being deactivated');
}
