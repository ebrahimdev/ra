import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { logInfo, logError } from './logger';

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

interface ProactiveCitationState {
  lastCheckTime: number;
  lastWordCount: number;
  insertedCitations: Set<string>;
  enabled: boolean;
}

export class CitationService {
  private static readonly API_BASE_URL = 'http://localhost:8000';
  private static readonly MAX_CHARS = 150;
  private static readonly SENTENCE_ENDINGS = ['.', '?', '!'];

  private static proactiveState: ProactiveCitationState = {
    lastCheckTime: 0,
    lastWordCount: 0,
    insertedCitations: new Set(),
    enabled: true
  };

  /**
   * Initialize proactive citation suggestions
   */
  static initializeProactiveSuggestions(context: vscode.ExtensionContext): void {
    // Load initial configuration
    this.loadConfiguration();

    // Listen to text document changes
    const textChangeDisposable = vscode.workspace.onDidChangeTextDocument(async (event) => {
      await this.handleTextChange(event);
    });

    // Listen to configuration changes
    const configChangeDisposable = vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration('quill')) {
        this.loadConfiguration();
      }
    });

    context.subscriptions.push(textChangeDisposable, configChangeDisposable);
  }

  /**
   * Load configuration settings
   */
  private static loadConfiguration(): void {
    const config = vscode.workspace.getConfiguration('quill.proactiveSuggestions');
    this.proactiveState.enabled = config.get('enabled', true);
  }

  /**
   * Toggle proactive suggestions on/off
   */
  static toggleProactiveSuggestions(): void {
    this.proactiveState.enabled = !this.proactiveState.enabled;

    const status = this.proactiveState.enabled ? 'enabled' : 'disabled';
    vscode.window.showInformationMessage(`Proactive citation suggestions ${status}`);

    // Update workspace configuration
    vscode.workspace.getConfiguration('quill.proactiveSuggestions').update('enabled', this.proactiveState.enabled, true);
  }

  /**
   * Get current proactive suggestions status
   */
  static isProactiveSuggestionsEnabled(): boolean {
    return this.proactiveState.enabled;
  }

  /**
   * Clear inserted citations tracking (useful for testing)
   */
  static clearInsertedCitationsTracking(): void {
    this.proactiveState.insertedCitations.clear();
  }

  /**
   * Get count of tracked inserted citations
   */
  static getInsertedCitationsCount(): number {
    return this.proactiveState.insertedCitations.size;
  }

  /**
 * Handle text document changes for proactive citation suggestions
 */
  private static async handleTextChange(event: vscode.TextDocumentChangeEvent): Promise<void> {
    const document = event.document;

    // Only process .tex files
    if (document.languageId !== 'latex') {
      return;
    }

    // Check if proactive suggestions are enabled
    if (!this.proactiveState.enabled) {

      return;
    }

    const now = Date.now();
    const currentWordCount = this.countWords(document.getText());





    // Check if we should trigger a citation suggestion
    const shouldCheck = this.shouldTriggerCitationCheck(
      event.contentChanges,
      currentWordCount,
      now
    );


    if (!shouldCheck) {
      return;
    }

    // Update state
    this.proactiveState.lastCheckTime = now;
    this.proactiveState.lastWordCount = currentWordCount;
    // Extract text around cursor and suggest citation
    await this.suggestProactiveCitation(document);
  }

  /**
 * Determine if we should trigger a citation check
 */
  private static shouldTriggerCitationCheck(
    contentChanges: readonly vscode.TextDocumentContentChangeEvent[],
    currentWordCount: number,
    now: number
  ): boolean {
    const config = vscode.workspace.getConfiguration('quill.proactiveSuggestions');
    const cooldownMs = config.get('cooldownMs', 8000);
    const wordThreshold = config.get('wordThreshold', 200);



    // Check cooldown
    if (now - this.proactiveState.lastCheckTime < cooldownMs) {

      return false;
    }

    // Check if a sentence was completed
    const hasSentenceEnding = contentChanges.some(change =>
      this.SENTENCE_ENDINGS.some(ending => change.text.includes(ending))
    );


    if (hasSentenceEnding) {

      return true;
    }

    // Check word threshold
    const wordDifference = currentWordCount - this.proactiveState.lastWordCount;

    if (wordDifference >= wordThreshold) {

      return true;
    }


    return false;
  }

  /**
   * Extract text around cursor for citation suggestion
   */
  private static extractTextAroundCursor(document: vscode.TextDocument): string {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document !== document) {
      return '';
    }

    const position = editor.selection.active;
    const fullText = document.getText();
    const offset = document.offsetAt(position);

    // Get text before cursor (up to MAX_CHARS)
    const startBefore = Math.max(0, offset - this.MAX_CHARS);
    const textBefore = fullText.substring(startBefore, offset);

    // Get text after cursor (up to 100 chars for context)
    const textAfter = fullText.substring(offset, Math.min(offset + 100, fullText.length));

    // Combine and find sentence boundaries
    const combinedText = textBefore + textAfter;
    const sentences = this.extractLastSentences(combinedText, textBefore.length);

    return sentences;
  }

  /**
   * Extract the last 1-2 sentences from text
   */
  private static extractLastSentences(text: string, cursorPosition: number): string {
    // Find sentence boundaries
    const sentences: string[] = [];
    let currentSentence = '';
    let charCount = 0;

    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      currentSentence += char;
      charCount++;

      if (this.SENTENCE_ENDINGS.includes(char) && (i + 1 >= text.length || text[i + 1] === ' ' || text[i + 1] === '\n')) {
        sentences.push(currentSentence.trim());
        currentSentence = '';

        // If we've found sentences and we're past the cursor, break
        if (charCount > cursorPosition && sentences.length >= 1) {
          break;
        }
      }
    }

    // Add any remaining text as a sentence
    if (currentSentence.trim()) {
      sentences.push(currentSentence.trim());
    }

    // Return the last 1-2 sentences
    const lastSentences = sentences.slice(-2);
    return lastSentences.join(' ').trim();
  }

  /**
   * Count words in text
   */
  private static countWords(text: string): number {
    return text.split(/\s+/).filter(word => word.length > 0).length;
  }

  /**
   * Suggest citation proactively
   */
  private static async suggestProactiveCitation(document: vscode.TextDocument): Promise<void> {
    try {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document !== document) {
        logInfo('No active editor or editor mismatch for proactive citation');
        return;
      }

      const position = editor.selection.active;


      // Use the unified reusable method with proactive flag
      await this.processCitationSuggestionAtPosition(document, position, vscode.window.activeTextEditor);

    } catch (error) {
      console.error('Error in proactive citation suggestion:', error);
    }
  }

  private static async insertCitationFromSuggestion(paper: CitationResponse['paper']): Promise<void> {
    if (!paper) {
      return;
    }

    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return;
    }

    try {
      this.insertCitation(editor, paper.citation_key);

      // Append bibtex entry
      const bibtexAdded = await this.appendBibtexEntry(paper.bibtex);

      if (bibtexAdded) {
        // Track inserted citation to avoid duplicates
        this.proactiveState.insertedCitations.add(paper.citation_key);

        vscode.window.showInformationMessage(`Citation inserted: ${paper.citation_key}`);
      } else {
        vscode.window.showWarningMessage(`Citation inserted but failed to update bibliography`);
      }
    } catch (error) {
      console.error('Error inserting citation:', error);
      vscode.window.showErrorMessage('Failed to insert citation');
    }
  }
  /**
   * Extract text from cursor position and send to backend for citation suggestion
   * @param document The text document
   * @param position The cursor position
   * @returns The citation response from backend
   */
  static async getCitationSuggestionAtPosition(document: vscode.TextDocument, position: vscode.Position): Promise<CitationResponse | null> {
    try {
      const fullText = document.getText();
      const offset = document.offsetAt(position);

      // Get the last 150 characters before the cursor
      const start = Math.max(0, offset - 150);
      const textBeforeCursor = fullText.substring(start, offset);
      const extractedText = textBeforeCursor.trim();

      if (!extractedText) {

        return null;
      }

      // Send to backend API
      return await this.suggestCitation(extractedText);
    } catch (error) {
      console.error('Error getting citation suggestion at position:', error);
      return null;
    }
  }

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
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }

      const data = await response.json();

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
      logInfo('Error creating refs.bib: ' + error);
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
      logInfo('Error appending bibtex entry: ' + error);
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


    logInfo('Showing citation suggestion: ' + message);
    const action = await vscode.window.showInformationMessage(
      message,
      'Insert Citation',
      'Dismiss'
    );

    logInfo('===============================================');
    logInfo('action: ' + action);
    logInfo('===============================================');

    return action === 'Insert Citation';
  }

  /**
   * Process citation suggestion at cursor position (reusable method)
   * @param document The text document
   * @param position The cursor position
   * @param editor The text editor (optional, for manual insertion)
   * @param isProactive Whether this is a proactive suggestion (affects UI behavior)
   * @returns Promise that resolves when processing is complete
   */
  static async processCitationSuggestionAtPosition(document: vscode.TextDocument, position: vscode.Position, editor?: vscode.TextEditor): Promise<void> {
    try {
      const response = await this.getCitationSuggestionAtPosition(document, position);

      if (!response) {
        return;
      }

      if (!response.match || !response.paper) {
        return;
      }

      logInfo('Citation suggestion: ' + response.paper.citation_key);
      const shouldInsert = await this.showCitationSuggestion(response.paper);

      logInfo('===============================================');
      logInfo('shouldInsert: ' + shouldInsert);
      logInfo('editor: ' + editor);
      logInfo('===============================================');


      if (shouldInsert && editor) {
        await this.insertCitationFromSuggestion(response.paper);
      }

    } catch (error) {
      vscode.window.showErrorMessage('An error occurred while processing citation suggestion');
    }
  }


} 