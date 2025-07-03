"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = __importStar(require("vscode"));
const citationService_1 = require("./citationService");
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
function activate(context) {
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
            const text = citationService_1.CitationService.extractTextFromEditor(editor);
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
                const response = await citationService_1.CitationService.suggestCitation(text);
                if (!response) {
                    vscode.window.showErrorMessage('Failed to get citation suggestion from server');
                    return;
                }
                if (!response.match || !response.paper) {
                    vscode.window.showInformationMessage('No relevant citation found for the selected text');
                    return;
                }
                // Show citation suggestion to user
                const shouldInsert = await citationService_1.CitationService.showCitationSuggestion(response.paper);
                if (shouldInsert) {
                    // Insert citation in the current file
                    citationService_1.CitationService.insertCitation(editor, response.paper.citation_key);
                    // Append bibtex entry to .bib file
                    const bibtexAdded = await citationService_1.CitationService.appendBibtexEntry(response.paper.bibtex);
                    if (bibtexAdded) {
                        vscode.window.showInformationMessage(`Citation inserted and bibliography updated!`);
                    }
                    else {
                        vscode.window.showWarningMessage(`Citation inserted but failed to update bibliography file`);
                    }
                }
            });
        }
        catch (error) {
            console.error('Error in suggestCitation command:', error);
            console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace available');
            vscode.window.showErrorMessage('An error occurred while suggesting citations');
        }
    });
    context.subscriptions.push(helloWorldDisposable, suggestCitationDisposable);
}
// This method is called when your extension is deactivated
function deactivate() {
    console.log('Quill extension is being deactivated');
}
//# sourceMappingURL=extension.js.map