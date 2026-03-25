import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FormsModule } from '@angular/forms';
import { NgDiagramComponent, initializeModel, provideNgDiagram } from 'ng-diagram';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, MatTabsModule, MatButtonModule, MatSnackBarModule, FormsModule, NgDiagramComponent],
  providers: [provideNgDiagram()],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  configContent = '';
  selectedTabIndex = 0;
  saving = false;
  reloading = false;
  originalContent = '';

  diagramModel = initializeModel({
    nodes: [
      { id: '1', position: { x: 100, y: 150 }, data: { label: 'Node 1' } },
      { id: '2', position: { x: 400, y: 150 }, data: { label: 'Node 2' } },
    ],
    edges: [
      {
        id: '1',
        source: '1',
        sourcePort: 'port-right',
        targetPort: 'port-left',
        target: '2',
        data: {},
      },
    ],
  });

  constructor(private snackBar: MatSnackBar) {}

  ngOnInit() {
    this.loadConfig();
  }

  async loadConfig() {
    try {
      const response = await fetch('/config');
      const data = await response.json();
      this.configContent = data.content;
      this.originalContent = data.content;
    } catch (error) {
      this.snackBar.open('Failed to load configuration', 'Close', { duration: 3000 });
    }
  }

  async saveConfig() {
    if (this.configContent === this.originalContent) {
      this.snackBar.open('No changes to save', 'Close', { duration: 2000 });
      return;
    }

    this.saving = true;
    try {
      const response = await fetch('/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: this.configContent })
      });

      if (response.ok) {
        this.originalContent = this.configContent;
        this.snackBar.open('Configuration saved successfully', 'Close', { duration: 3000 });
      } else {
        throw new Error('Save failed');
      }
    } catch (error) {
      this.snackBar.open('Failed to save configuration', 'Close', { duration: 3000 });
    } finally {
      this.saving = false;
    }
  }

  async reloadServer() {
    this.reloading = true;
    try {
      const response = await fetch('/config/reload', { method: 'POST' });

      if (response.ok) {
        this.snackBar.open('Server configuration reloaded', 'Close', { duration: 3000 });
      } else {
        throw new Error('Reload failed');
      }
    } catch (error) {
      this.snackBar.open('Failed to reload server', 'Close', { duration: 3000 });
    } finally {
      this.reloading = false;
    }
  }
}
