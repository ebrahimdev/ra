import * as vscode from 'vscode';

export const quillOutput = vscode.window.createOutputChannel("Quill Logs");


export function logInfo(msg: string) {
  quillOutput.appendLine(`[INFO] ${msg}`);
}

export function logError(err: any) {
  quillOutput.appendLine(`[ERROR] ${err instanceof Error ? err.message : String(err)}`);
}
