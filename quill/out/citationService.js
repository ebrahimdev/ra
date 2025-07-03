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
exports.CitationService = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
class CitationService {
    static API_BASE_URL = 'http://localhost:8000';
    /**
   * Extract text from the current editor
   * @param editor The active text editor
   * @returns The last 150 characters before the cursor
   */
    static extractTextFromEditor(editor) {
        const document = editor.document;
        const position = editor.selection.active;
        const fullText = document.getText();
        const offset = document.offsetAt(position);
        // Get the last 150 characters before the cursor
        const start = Math.max(0, offset - 150);
        const textBeforeCursor = fullText.substring(start, offset);
        return textBeforeCursor.trim();
    }
    /**
     * Send text to the backend for citation suggestion
     */
    static async suggestCitation(text) {
        try {
            const url = `${this.API_BASE_URL}/api/v1/suggest-citation`;
            const requestBody = { text };
            console.log('Making API request to:', url);
            console.log('Request body:', requestBody);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response error text:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
            }
            const data = await response.json();
            console.log('Response data:', data);
            return data;
        }
        catch (error) {
            console.error('Error suggesting citation:', error);
            return null;
        }
    }
    /**
     * Insert citation at current cursor position
     */
    static insertCitation(editor, citationKey) {
        const position = editor.selection.active;
        const citationText = `\\cite{${citationKey}}`;
        editor.edit(editBuilder => {
            editBuilder.insert(position, citationText);
        });
    }
    /**
     * Find or create .bib file in the workspace
     */
    static async findOrCreateBibFile() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return null;
        }
        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        // Look for existing .bib files
        const bibFiles = await vscode.workspace.findFiles('**/*.bib');
        if (bibFiles.length > 0) {
            return bibFiles[0].fsPath;
        }
        // Create refs.bib if no .bib file exists
        const refsBibPath = path.join(workspaceRoot, 'refs.bib');
        try {
            if (!fs.existsSync(refsBibPath)) {
                fs.writeFileSync(refsBibPath, '% Bibliography file\n\n');
            }
            return refsBibPath;
        }
        catch (error) {
            console.error('Error creating refs.bib:', error);
            return null;
        }
    }
    /**
     * Append bibtex entry to .bib file
     */
    static async appendBibtexEntry(bibtex) {
        try {
            const bibFilePath = await this.findOrCreateBibFile();
            if (!bibFilePath) {
                return false;
            }
            // Read existing content
            const existingContent = fs.readFileSync(bibFilePath, 'utf8');
            // Append new entry
            const newContent = existingContent + '\n' + bibtex + '\n';
            fs.writeFileSync(bibFilePath, newContent);
            return true;
        }
        catch (error) {
            console.error('Error appending bibtex entry:', error);
            return false;
        }
    }
    /**
     * Show citation suggestion notification
     */
    static async showCitationSuggestion(paper) {
        if (!paper) {
            return false;
        }
        const message = `💡 Possible citation: ${paper.citation_key}\n"${paper.match_snippet}"`;
        const action = await vscode.window.showInformationMessage(message, 'Insert Citation', 'Cancel');
        return action === 'Insert Citation';
    }
}
exports.CitationService = CitationService;
//# sourceMappingURL=citationService.js.map