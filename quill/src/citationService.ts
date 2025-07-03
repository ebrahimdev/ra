import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface CitationResponse {
  match: boolean;
  score: number;
  paper?: {
    title: string;
    authors: string;
    citation_key: string;
    bibtex: string;
    match_snippet?: string;
  };
}

export class CitationService {
  private static readonly API_BASE_URL = 'http://localhost:8000';

  /**
 * Extract text from the current editor
 * @param editor The active text editor
 * @returns The last 150 characters before the cursor
 */
  static extractTextFromEditor(editor: vscode.TextEditor): string {
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
  static async suggestCitation(text: string): Promise<CitationResponse | null> {
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
      return data as CitationResponse;
    } catch (error) {
      console.error('Error suggesting citation:', error);
      return null;
    }
  }

  /**
   * Insert citation at current cursor position
   */
  static insertCitation(editor: vscode.TextEditor, citationKey: string): void {
    const position = editor.selection.active;
    const citationText = `\\cite{${citationKey}}`;

    editor.edit(editBuilder => {
      editBuilder.insert(position, citationText);
    });
  }

  /**
   * Find or create .bib file in the workspace
   */
  static async findOrCreateBibFile(): Promise<string | null> {
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
    } catch (error) {
      console.error('Error creating refs.bib:', error);
      return null;
    }
  }

  /**
   * Append bibtex entry to .bib file
   */
  static async appendBibtexEntry(bibtex: string): Promise<boolean> {
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
    } catch (error) {
      console.error('Error appending bibtex entry:', error);
      return false;
    }
  }

  /**
   * Show citation suggestion notification
   */
  static async showCitationSuggestion(paper: CitationResponse['paper']): Promise<boolean> {
    if (!paper) {
      return false;
    }

    const message = `💡 Possible citation: ${paper.citation_key}\n"${paper.match_snippet}"`;

    const action = await vscode.window.showInformationMessage(
      message,
      'Insert Citation',
      'Cancel'
    );

    return action === 'Insert Citation';
  }
} 