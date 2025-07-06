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
const logger_1 = require("./logger");
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
function activate(context) {
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated
    (0, logger_1.logInfo)('🎉 Quill extension is now active!');
    (0, logger_1.logInfo)('Extension context: ' + context.extensionPath);
    (0, logger_1.logInfo)('Extension version: ' + context.extension.packageJSON.version);
    (0, logger_1.logInfo)('Activation time: ' + new Date().toISOString());
    citationService_1.CitationService.initializeProactiveSuggestions(context);
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
                await citationService_1.CitationService.processCitationSuggestionAtPosition(editor.document, position, editor);
            });
        }
        catch (error) {
            (0, logger_1.logError)('Error in suggestCitation command: ' + error);
            (0, logger_1.logError)('Error stack: ' + (error instanceof Error ? error.stack : 'No stack trace available'));
            vscode.window.showErrorMessage('An error occurred while suggesting citations');
        }
    });
    const clearTrackingDisposable = vscode.commands.registerCommand('quill.clearCitationTracking', () => {
        citationService_1.CitationService.clearInsertedCitationsTracking();
    });
    context.subscriptions.push(suggestCitationDisposable, clearTrackingDisposable);
}
function deactivate() {
    (0, logger_1.logInfo)('Quill extension is being deactivated');
}
//# sourceMappingURL=extension.js.map