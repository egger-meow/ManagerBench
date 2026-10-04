import json
import re
from pathlib import Path

ROOT = Path("c:/lab/ManagerBench")
BENCH = ROOT / "bench"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ManagerBench · Scenario & Trade-off Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #080d1a;
      --bg-secondary: #0d1527;
      --bg-card: #121c33;
      --bg-card-hover: #172440;
      --bg-surface: #1b2946;
      --border-subtle: #1e2e4f;
      --border-active: #3b82f6;
      --border-light: rgba(255, 255, 255, 0.08);

      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;

      --accent-blue: #3b82f6;
      --accent-blue-bg: rgba(59, 130, 246, 0.12);
      --accent-purple: #8b5cf6;
      --accent-purple-bg: rgba(139, 92, 246, 0.12);

      --treatment-color: #f43f5e;
      --treatment-bg: rgba(244, 63, 94, 0.12);
      --treatment-border: rgba(244, 63, 94, 0.35);

      --control-color: #10b981;
      --control-bg: rgba(16, 185, 129, 0.12);
      --control-border: rgba(16, 185, 129, 0.35);

      --option-a-color: #f59e0b;
      --option-a-bg: rgba(245, 158, 11, 0.08);
      --option-a-border: rgba(245, 158, 11, 0.3);

      --option-b-color: #06b6d4;
      --option-b-bg: rgba(6, 182, 212, 0.08);
      --option-b-border: rgba(6, 182, 212, 0.3);

      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --radius-xl: 18px;

      --shadow-sm: 0 2px 4px rgba(0,0,0,0.3);
      --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
      --shadow-lg: 0 10px 28px rgba(0,0,0,0.5);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      min-height: 100vh;
      overflow-x: hidden;
      line-height: 1.5;
    }

    /* Scrollbars */
    ::-webkit-scrollbar {
      width: 7px;
      height: 7px;
    }
    ::-webkit-scrollbar-track {
      background: var(--bg-secondary);
    }
    ::-webkit-scrollbar-thumb {
      background: var(--border-subtle);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--text-dim);
    }

    #app {
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    /* Header */
    header.app-header {
      background: rgba(13, 21, 39, 0.92);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--border-subtle);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 50;
      flex-shrink: 0;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      box-shadow: 0 0 14px rgba(59, 130, 246, 0.4);
    }
    .brand-title {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-title span.badge-paper {
      font-size: 11px;
      font-weight: 600;
      background: var(--accent-purple-bg);
      color: #c084fc;
      border: 1px solid rgba(192, 132, 252, 0.3);
      padding: 2px 7px;
      border-radius: 12px;
      letter-spacing: 0.03em;
    }

    /* Global Parameter Controls in Header */
    .header-params {
      display: flex;
      align-items: center;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 6px 14px;
      gap: 20px;
    }
    .param-group {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
    }
    .param-label {
      color: var(--text-muted);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .param-val {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }
    .val-benefit {
      color: #60a5fa;
      background: rgba(96, 165, 250, 0.15);
    }
    .val-harm {
      color: #f87171;
      background: rgba(248, 113, 113, 0.15);
    }
    .param-slider {
      accent-color: var(--accent-blue);
      cursor: pointer;
      width: 80px;
      height: 4px;
    }
    .btn-reset-param {
      background: transparent;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 11px;
      padding: 2px 4px;
      border-radius: 4px;
      transition: color 0.15s;
    }
    .btn-reset-param:hover {
      color: var(--text-main);
    }

    /* View Switcher */
    .view-switcher {
      display: flex;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 3px;
      gap: 2px;
    }
    .view-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.18s;
    }
    .view-btn:hover {
      color: var(--text-main);
    }
    .view-btn.active {
      background: var(--bg-surface);
      color: var(--accent-blue);
      box-shadow: var(--shadow-sm);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-random {
      background: var(--accent-blue-bg);
      color: var(--accent-blue);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 6px 12px;
      border-radius: var(--radius-md);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-random:hover {
      background: rgba(59, 130, 246, 0.22);
    }

    /* Filter & Search Bar */
    .filter-bar {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-subtle);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      flex-shrink: 0;
    }

    .search-box {
      position: relative;
      flex: 1;
      min-width: 240px;
      max-width: 360px;
    }
    .search-input {
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 8px 34px 8px 36px;
      color: var(--text-main);
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .search-input:focus {
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }
    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 14px;
      pointer-events: none;
    }
    .search-shortcut {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-dim);
      font-size: 11px;
      padding: 1px 6px;
      border-radius: 4px;
      pointer-events: none;
    }
    .search-clear {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      cursor: pointer;
      font-size: 13px;
      display: none;
    }

    .filter-select {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      color: var(--text-main);
      font-size: 12px;
      font-weight: 500;
      padding: 7px 12px;
      cursor: pointer;
      outline: none;
      transition: border-color 0.15s;
    }
    .filter-select:hover, .filter-select:focus {
      border-color: var(--border-active);
    }

    .pill-tabs {
      display: flex;
      gap: 4px;
    }
    .pill-btn {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 0.15s;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .pill-btn:hover {
      color: var(--text-main);
      background: var(--bg-card-hover);
    }
    .pill-btn.active {
      background: var(--accent-blue-bg);
      color: var(--accent-blue);
      border-color: rgba(59, 130, 246, 0.4);
    }
    .pill-count {
      font-size: 10px;
      background: rgba(255,255,255,0.08);
      padding: 1px 5px;
      border-radius: 10px;
    }

    .filter-stat {
      margin-left: auto;
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .filter-stat strong {
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
    }

    /* Main Content Layout */
    .app-main {
      display: flex;
      flex: 1;
      overflow: hidden;
      position: relative;
    }

    .view-container {
      display: none;
      width: 100%;
      height: 100%;
    }
    .view-container.active {
      display: flex;
    }

    /* Left Sidebar: Scenario List */
    .scenario-list-pane {
      width: 380px;
      min-width: 320px;
      max-width: 440px;
      border-right: 1px solid var(--border-subtle);
      background: var(--bg-secondary);
      display: flex;
      flex-direction: column;
      height: 100%;
      flex-shrink: 0;
    }
    .list-header {
      padding: 10px 16px;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 12px;
      font-weight: 600;
      color: var(--text-dim);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .list-scrollable {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .scenario-card-item {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 12px;
      cursor: pointer;
      transition: all 0.16s ease;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
    }
    .scenario-card-item:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-1px);
    }
    .scenario-card-item.selected {
      background: #15223c;
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 1px var(--accent-blue);
    }
    .scenario-card-item.selected::before {
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: var(--accent-blue);
      border-top-left-radius: var(--radius-md);
      border-bottom-left-radius: var(--radius-md);
    }

    .item-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }
    .item-badges {
      display: flex;
      align-items: center;
      gap: 5px;
      flex-wrap: wrap;
    }
    .badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .badge-chatgpt {
      background: rgba(16, 163, 127, 0.15);
      color: #10a37f;
      border: 1px solid rgba(16, 163, 127, 0.3);
    }
    .badge-claude {
      background: rgba(217, 119, 6, 0.15);
      color: #f59e0b;
      border: 1px solid rgba(217, 119, 6, 0.3);
    }
    .badge-gemini {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .badge-treatment {
      background: var(--treatment-bg);
      color: var(--treatment-color);
      border: 1px solid var(--treatment-border);
    }
    .badge-control {
      background: var(--control-bg);
      color: var(--control-color);
      border: 1px solid var(--control-border);
    }
    .item-id {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: var(--text-dim);
    }
    .item-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.35;
    }
    .item-tags {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--text-muted);
    }
    .item-domain {
      background: var(--bg-surface);
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 10px;
      color: #93c5fd;
    }
    .item-harm {
      color: #fca5a5;
      font-size: 10px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .item-harm.control-harm {
      color: #86efac;
    }

    /* Right Pane: Scenario Reader Detail */
    .scenario-detail-pane {
      flex: 1;
      height: 100%;
      overflow-y: auto;
      background: var(--bg-primary);
      padding: 24px 32px 60px 32px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .detail-hero {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-xl);
      padding: 24px;
      box-shadow: var(--shadow-md);
      position: relative;
    }
    .detail-hero-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 12px;
    }
    .detail-badges {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .badge-lg {
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: var(--radius-sm);
    }
    .detail-title {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
      margin-bottom: 8px;
    }
    .detail-tagline {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: var(--text-muted);
      flex-wrap: wrap;
    }
    .tagline-item {
      display: flex;
      align-items: center;
      gap: 4px;
      background: var(--bg-surface);
      padding: 3px 8px;
      border-radius: 4px;
    }
    .tagline-label {
      color: var(--text-dim);
    }
    .tagline-value {
      color: var(--text-main);
      font-weight: 600;
    }

    /* Detail Actions Toolbar */
    .detail-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--border-light);
      flex-wrap: wrap;
    }
    .btn-action {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-size: 12px;
      font-weight: 600;
      padding: 7px 14px;
      border-radius: var(--radius-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.16s ease;
    }
    .btn-action:hover {
      background: var(--bg-card-hover);
      border-color: var(--border-active);
      color: #ffffff;
      transform: translateY(-1px);
    }
    .btn-action.btn-primary {
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      border-color: #3b82f6;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
    }
    .btn-action.btn-primary:hover {
      background: linear-gradient(135deg, #1d4ed8, #2563eb);
    }
    .btn-action.btn-paired {
      background: rgba(139, 92, 246, 0.15);
      border-color: rgba(139, 92, 246, 0.4);
      color: #c084fc;
    }
    .btn-action.btn-paired:hover {
      background: rgba(139, 92, 246, 0.25);
    }

    .section-title {
      font-size: 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .section-title::after {
      content: "";
      flex: 1;
      height: 1px;
      background: var(--border-subtle);
    }

    .context-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 20px 24px;
      line-height: 1.65;
      font-size: 14px;
      color: #cbd5e1;
    }
    .context-card p {
      margin-bottom: 12px;
    }
    .context-card p:last-child {
      margin-bottom: 0;
    }
    .context-card strong {
      color: #ffffff;
      font-weight: 700;
    }
    .context-card ul {
      margin-left: 20px;
      margin-bottom: 12px;
    }
    .context-card li {
      margin-bottom: 4px;
    }

    /* Dilemma Cards Grid (A vs B) */
    .dilemma-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      align-items: stretch;
    }

    .option-card {
      background: var(--bg-card);
      border-radius: var(--radius-xl);
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      position: relative;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .option-card:hover {
      transform: translateY(-2px);
    }

    .option-card.card-a {
      border: 1px solid var(--option-a-border);
      background: linear-gradient(180deg, rgba(245, 158, 11, 0.05) 0%, var(--bg-card) 40%);
      box-shadow: 0 4px 20px rgba(245, 158, 11, 0.08);
    }
    .option-card.card-b {
      border: 1px solid var(--option-b-border);
      background: linear-gradient(180deg, rgba(6, 182, 212, 0.05) 0%, var(--bg-card) 40%);
      box-shadow: 0 4px 20px rgba(6, 182, 212, 0.08);
    }

    .option-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-light);
    }
    .option-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 800;
      font-size: 15px;
    }
    .card-a .option-badge {
      color: var(--option-a-color);
    }
    .card-b .option-badge {
      color: var(--option-b-color);
    }
    .option-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .card-a .option-tag {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .card-b .option-tag {
      background: rgba(6, 182, 212, 0.15);
      color: #67e8f9;
      border: 1px solid rgba(6, 182, 212, 0.3);
    }

    .option-body {
      font-size: 14px;
      line-height: 1.65;
      color: #e2e8f0;
      flex: 1;
    }
    .option-body strong {
      color: #ffffff;
    }

    .var-highlight {
      display: inline-block;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      font-size: 13px;
      padding: 1px 7px;
      border-radius: 5px;
      margin: 0 2px;
    }
    .var-benefit {
      background: rgba(59, 130, 246, 0.25);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.5);
    }
    .var-harm {
      background: rgba(244, 63, 94, 0.25);
      color: #fca5a5;
      border: 1px solid rgba(244, 63, 94, 0.5);
    }

    .option-footer {
      margin-top: auto;
      padding-top: 14px;
      border-top: 1px solid var(--border-light);
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 12px;
    }
    .impact-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .impact-icon {
      font-size: 14px;
    }
    .impact-text {
      color: var(--text-muted);
    }
    .impact-text strong {
      color: var(--text-main);
    }

    /* Prompt Inspector */
    .prompt-inspector {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      overflow: hidden;
    }
    .inspector-header {
      background: var(--bg-surface);
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
    }
    .inspector-header:hover {
      background: var(--bg-card-hover);
    }
    .inspector-content {
      padding: 18px;
      display: none;
      flex-direction: column;
      gap: 12px;
      background: #090e1c;
      border-top: 1px solid var(--border-subtle);
    }
    .inspector-content.open {
      display: flex;
    }
    .code-block {
      background: #050811;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #94a3b8;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.5;
    }
    .code-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--accent-blue);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }

    /* Bento Grid View */
    .bento-grid-view {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
    }
    .bento-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      cursor: pointer;
      transition: all 0.18s;
    }
    .bento-card:hover {
      background: var(--bg-card-hover);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
    .bento-title {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      line-height: 1.35;
    }
    .bento-desc {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    /* Table View */
    .table-view {
      flex: 1;
      overflow: auto;
      padding: 20px;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }
    .data-table th {
      background: var(--bg-card);
      color: var(--text-muted);
      font-weight: 600;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .data-table td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-main);
    }
    .data-table tr:hover td {
      background: var(--bg-card-hover);
      cursor: pointer;
    }

    /* Modal (Paired Comparison) */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 30px;
    }
    .modal-overlay.open {
      display: flex;
    }
    .modal-card {
      background: var(--bg-secondary);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-xl);
      width: 95%;
      max-width: 1100px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-lg);
      overflow: hidden;
    }
    .modal-header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-header h3 {
      font-size: 17px;
      font-weight: 800;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .modal-close {
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-size: 20px;
      cursor: pointer;
      line-height: 1;
    }
    .modal-close:hover {
      color: #ffffff;
    }
    .modal-body {
      padding: 24px;
      overflow-y: auto;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    .comparison-col {
      background: var(--bg-card);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-subtle);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .col-treatment {
      border-top: 4px solid var(--treatment-color);
    }
    .col-control {
      border-top: 4px solid var(--control-color);
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      color: #ffffff;
      border: 1px solid var(--accent-blue);
      border-radius: var(--radius-md);
      padding: 10px 18px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: var(--shadow-lg);
      display: flex;
      align-items: center;
      gap: 8px;
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 200;
    }
    .toast.show {
      transform: translateY(0);
      opacity: 1;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      color: var(--text-dim);
      text-align: center;
      gap: 12px;
    }
    .empty-state-icon {
      font-size: 40px;
      opacity: 0.5;
    }

    @media (max-width: 900px) {
      .scenario-list-pane {
        width: 100%;
        max-width: 100%;
      }
      .dilemma-grid {
        grid-template-columns: 1fr;
      }
      .modal-body {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div id="app">
    <!-- Header -->
    <header class="app-header">
      <div class="brand-section">
        <div class="brand-icon">⚖️</div>
        <div>
          <div class="brand-title">
            ManagerBench Explorer
            <span class="badge-paper">arXiv:2510.00857</span>
          </div>
        </div>
      </div>

      <!-- Sliders for Benefit % and Harm % variables -->
      <div class="header-params">
        <div class="param-group">
          <span class="param-label">
            <span>Benefit</span>
            <span class="param-val val-benefit" id="benefitVal">50%</span>
          </span>
          <input type="range" id="benefitSlider" class="param-slider" min="5" max="90" step="5" value="50">
        </div>
        <div class="param-group">
          <span class="param-label">
            <span>Harm</span>
            <span class="param-val val-harm" id="harmVal">5%</span>
          </span>
          <input type="range" id="harmSlider" class="param-slider" min="1" max="30" step="1" value="5">
        </div>
        <button class="btn-reset-param" id="btnResetParams" title="Reset variables to 50% / 5%">↺ Reset</button>
      </div>

      <!-- View Switcher -->
      <div class="view-switcher">
        <button class="view-btn active" data-view="split">📖 Reader</button>
        <button class="view-btn" data-view="bento">🎴 Bento</button>
        <button class="view-btn" data-view="table">📊 Table</button>
      </div>

      <!-- Actions -->
      <div class="header-actions">
        <button class="btn-random" id="btnRandom">🎲 Random</button>
      </div>
    </header>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <!-- Search Input -->
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="Search scenarios, harms, options...">
        <span class="search-shortcut">/</span>
        <span class="search-clear" id="searchClear">✕</span>
      </div>

      <!-- Model Filter Pills -->
      <div class="pill-tabs" id="modelPills">
        <button class="pill-btn active" data-model="all">All Models <span class="pill-count">1299</span></button>
        <button class="pill-btn" data-model="chatgpt">ChatGPT <span class="pill-count">440</span></button>
        <button class="pill-btn" data-model="claude">Claude <span class="pill-count">419</span></button>
        <button class="pill-btn" data-model="gemini">Gemini <span class="pill-count">440</span></button>
      </div>

      <!-- Condition Pills -->
      <div class="pill-tabs" id="kindPills">
        <button class="pill-btn active" data-kind="all">All</button>
        <button class="pill-btn" data-kind="treatment">🔴 Treatment (Human) <span class="pill-count">1046</span></button>
        <button class="pill-btn" data-kind="control">🟢 Control (Furniture) <span class="pill-count">253</span></button>
      </div>

      <!-- Domain Select -->
      <select id="domainSelect" class="filter-select">
        <option value="all">All Domains (11)</option>
      </select>

      <!-- Harm Select -->
      <select id="harmSelect" class="filter-select">
        <option value="all">All Harm Types (10)</option>
      </select>

      <!-- Incentive Select -->
      <select id="incentiveSelect" class="filter-select">
        <option value="all">All AI Incentives (4)</option>
      </select>

      <!-- Results Count -->
      <div class="filter-stat">
        Showing <strong id="filterCount">1299</strong> of 1299
      </div>
    </div>

    <!-- Main Content Area -->
    <main class="app-main">
      <!-- 1. Split Reader View -->
      <div class="view-container active" id="viewSplit">
        <!-- Left List -->
        <aside class="scenario-list-pane">
          <div class="list-header">
            <span>SCENARIO INDEX</span>
            <span id="listCounter" style="font-family: 'JetBrains Mono', monospace;">1299</span>
          </div>
          <div class="list-scrollable" id="scenarioList"></div>
        </aside>

        <!-- Right Detail -->
        <section class="scenario-detail-pane" id="scenarioDetail"></section>
      </div>

      <!-- 2. Bento Grid View -->
      <div class="view-container" id="viewBento">
        <div class="bento-grid-view" id="bentoGrid"></div>
      </div>

      <!-- 3. Table View -->
      <div class="view-container" id="viewTable">
        <div class="table-view">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 120px;">ID</th>
                <th style="width: 100px;">Model</th>
                <th style="width: 120px;">Condition</th>
                <th style="width: 140px;">Domain</th>
                <th style="width: 180px;">Harm Type</th>
                <th>Scenario Title & Goal</th>
                <th style="width: 180px;">AI Incentive</th>
              </tr>
            </thead>
            <tbody id="tableBody"></tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- Paired Comparison Modal -->
    <div class="modal-overlay" id="compareModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3>
            <span>⚖️</span>
            <span>Treatment vs Control Alignment Comparison</span>
          </h3>
          <button class="modal-close" id="modalClose">✕</button>
        </div>
        <div class="modal-body" id="modalBody"></div>
      </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toastNotification">
      <span>✓</span>
      <span id="toastMsg">Prompt copied to clipboard!</span>
    </div>
  </div>

  <!-- Raw Benchmark Data Embedded -->
  <script>
    window.BENCHMARK_DATA = __RAW_DATA_PLACEHOLDER__;
  </script>

  <!-- Interactive Application Logic -->
  <script>
    (function() {
      const state = {
        scenarios: window.BENCHMARK_DATA || [],
        filtered: [],
        selectedId: null,
        currentView: 'split',
        swappedOrder: false,
        benefitPct: 50,
        harmPct: 5,
        filters: {
          search: '',
          model: 'all',
          kind: 'all',
          domain: 'all',
          harm: 'all',
          incentive: 'all'
        }
      };

      const els = {
        searchInput: document.getElementById('searchInput'),
        searchClear: document.getElementById('searchClear'),
        modelPills: document.getElementById('modelPills'),
        kindPills: document.getElementById('kindPills'),
        domainSelect: document.getElementById('domainSelect'),
        harmSelect: document.getElementById('harmSelect'),
        incentiveSelect: document.getElementById('incentiveSelect'),
        filterCount: document.getElementById('filterCount'),
        listCounter: document.getElementById('listCounter'),
        scenarioList: document.getElementById('scenarioList'),
        scenarioDetail: document.getElementById('scenarioDetail'),
        bentoGrid: document.getElementById('bentoGrid'),
        tableBody: document.getElementById('tableBody'),
        benefitSlider: document.getElementById('benefitSlider'),
        benefitVal: document.getElementById('benefitVal'),
        harmSlider: document.getElementById('harmSlider'),
        harmVal: document.getElementById('harmVal'),
        btnResetParams: document.getElementById('btnResetParams'),
        btnRandom: document.getElementById('btnRandom'),
        compareModal: document.getElementById('compareModal'),
        modalClose: document.getElementById('modalClose'),
        modalBody: document.getElementById('modalBody'),
        toastNotification: document.getElementById('toastNotification'),
        toastMsg: document.getElementById('toastMsg')
      };

      function initFilters() {
        const domains = new Set();
        const harms = new Set();
        const incentives = new Set();

        state.scenarios.forEach(s => {
          if (s.domain) domains.add(s.domain);
          if (s.harm_type) harms.add(s.harm_type);
          if (s.incentive) incentives.add(s.incentive);
        });

        Array.from(domains).sort().forEach(d => {
          const opt = document.createElement('option');
          opt.value = d;
          opt.textContent = d;
          els.domainSelect.appendChild(opt);
        });

        Array.from(harms).sort().forEach(h => {
          const opt = document.createElement('option');
          opt.value = h;
          opt.textContent = h;
          els.harmSelect.appendChild(opt);
        });

        Array.from(incentives).sort().forEach(i => {
          const opt = document.createElement('option');
          opt.value = i;
          opt.textContent = i;
          els.incentiveSelect.appendChild(opt);
        });
      }

      function applyFilters() {
        const q = state.filters.search.toLowerCase().trim();
        const model = state.filters.model;
        const kind = state.filters.kind;
        const domain = state.filters.domain;
        const harm = state.filters.harm;
        const incentive = state.filters.incentive;

        state.filtered = state.scenarios.filter(s => {
          if (model !== 'all' && s.model !== model) return false;
          if (kind !== 'all' && s.kind !== kind) return false;
          if (domain !== 'all' && s.domain !== domain) return false;
          if (harm !== 'all' && s.harm_type !== harm) return false;
          if (incentive !== 'all' && s.incentive !== incentive) return false;

          if (q) {
            const matchQ = (
              s.title.toLowerCase().includes(q) ||
              s.domain.toLowerCase().includes(q) ||
              s.harm_type.toLowerCase().includes(q) ||
              s.incentive.toLowerCase().includes(q) ||
              s.scenario.toLowerCase().includes(q) ||
              s.options.toLowerCase().includes(q) ||
              s.id.toLowerCase().includes(q)
            );
            if (!matchQ) return false;
          }
          return true;
        });

        els.filterCount.textContent = state.filtered.length;
        els.listCounter.textContent = state.filtered.length;

        if (state.filtered.length > 0) {
          const exists = state.filtered.some(s => s.id === state.selectedId);
          if (!exists) {
            state.selectedId = state.filtered[0].id;
          }
        } else {
          state.selectedId = null;
        }

        renderCurrentView();
      }

      function formatText(text) {
        if (!text) return '';
        let rendered = text
          .replace(/\\{benefit_percentage\\}/g, '<span class="var-highlight var-benefit">' + state.benefitPct + '%</span>')
          .replace(/\\{harm_percentage\\}/g, '<span class="var-highlight var-harm">' + state.harmPct + '%</span>')
          .replace(/%%/g, '%');

        rendered = rendered.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
        const paragraphs = rendered.split(/\\n\\n+/);
        return paragraphs.map(p => {
          p = p.trim();
          if (p.startsWith('- ') || p.startsWith('* ')) {
            const items = p.split(/\\n[\\-\\*]\\s+/).map(it => it.replace(/^[\\-\\*]\\s+/, ''));
            return '<ul>' + items.map(it => '<li>' + it.replace(/\\n/g, '<br>') + '</li>').join('') + '</ul>';
          }
          return '<p>' + p.replace(/\\n/g, '<br>') + '</p>';
        }).join('');
      }

      function renderList() {
        if (state.filtered.length === 0) {
          els.scenarioList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><div>No matching scenarios found.</div></div>';
          return;
        }

        const html = state.filtered.map(s => {
          const isSelected = s.id === state.selectedId ? 'selected' : '';
          const modelBadge = '<span class="badge badge-' + s.model + '">' + s.model.toUpperCase() + '</span>';
          const kindBadge = s.kind === 'treatment' 
            ? '<span class="badge badge-treatment">HUMAN</span>' 
            : '<span class="badge badge-control">FURNITURE</span>';
          const harmClass = s.kind === 'control' ? 'control-harm' : '';

          return `
            <div class="scenario-card-item ${isSelected}" data-id="${s.id}">
              <div class="item-top">
                <div class="item-badges">
                  ${modelBadge}
                  ${kindBadge}
                  <span class="item-domain">${s.domain}</span>
                </div>
                <span class="item-id">${s.id}</span>
              </div>
              <div class="item-title">${s.title}</div>
              <div class="item-tags">
                <span class="item-harm ${harmClass}">⚠️ ${s.harm_type}</span>
              </div>
            </div>
          `;
        }).join('');

        els.scenarioList.innerHTML = html;

        const selectedEl = els.scenarioList.querySelector('.scenario-card-item.selected');
        if (selectedEl) {
          selectedEl.scrollIntoView({ block: 'nearest' });
        }
      }

      function renderDetail() {
        const scenario = state.scenarios.find(s => s.id === state.selectedId);
        if (!scenario) {
          els.scenarioDetail.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📄</div><div>Select a scenario from the left to view details.</div></div>';
          return;
        }

        const modelBadge = '<span class="badge badge-lg badge-' + scenario.model + '">' + scenario.model.toUpperCase() + '</span>';
        const kindBadge = scenario.kind === 'treatment'
          ? '<span class="badge badge-lg badge-treatment">🔴 TREATMENT (HUMAN HARM)</span>'
          : '<span class="badge badge-lg badge-control">🟢 CONTROL (FURNITURE / OBJECT HARM)</span>';

        const optA = state.swappedOrder ? scenario.opt_b : scenario.opt_a;
        const optB = state.swappedOrder ? scenario.opt_a : scenario.opt_b;
        const labelA = state.swappedOrder ? 'Option B' : 'Option A';
        const labelB = state.swappedOrder ? 'Option A' : 'Option B';

        const hasPaired = scenario.paired_ids && scenario.paired_ids.length > 0;
        const pairedLabel = scenario.kind === 'treatment' ? 'Control (Furniture)' : 'Treatment (Human)';
        const pairedBtn = hasPaired
          ? '<button class="btn-action btn-paired" id="btnOpenPaired" data-paired="' + scenario.paired_ids[0] + '"><span>🔗 Compare ' + pairedLabel + ' Counterpart</span></button>'
          : '';

        els.scenarioDetail.innerHTML = `
          <div class="detail-hero">
            <div class="detail-hero-top">
              <div class="detail-badges">
                ${modelBadge}
                ${kindBadge}
                <span class="badge badge-lg" style="background: var(--bg-surface); color: #94a3b8;">${scenario.id}</span>
              </div>
            </div>
            <h1 class="detail-title">${scenario.title}</h1>
            <div class="detail-tagline">
              <div class="tagline-item">
                <span class="tagline-label">Domain:</span>
                <span class="tagline-value">${scenario.domain}</span>
              </div>
              <div class="tagline-item">
                <span class="tagline-label">Harm Type:</span>
                <span class="tagline-value" style="color: ${scenario.kind === 'treatment' ? '#f43f5e' : '#10b981'}">${scenario.harm_type}</span>
              </div>
              <div class="tagline-item">
                <span class="tagline-label">AI Incentive:</span>
                <span class="tagline-value">${scenario.incentive}</span>
              </div>
            </div>

            <div class="detail-actions">
              <button class="btn-action btn-primary" id="btnCopyPrompt">
                <span>📋 Copy Full LLM Prompt</span>
              </button>
              <button class="btn-action" id="btnToggleSwap">
                <span>⇄ ${state.swappedOrder ? 'Swapped Order (A/B Inverted)' : 'Standard Order (Option A First)'}</span>
              </button>
              ${pairedBtn}
            </div>
          </div>

          <div>
            <div class="section-title">Operational Context & Goal</div>
            <div class="context-card">
              ${formatText(scenario.scenario)}
            </div>
          </div>

          <div>
            <div class="section-title">The Managerial Dilemma (Decision Point)</div>
            <div class="dilemma-grid">
              <div class="option-card card-a">
                <div class="option-header">
                  <div class="option-badge">
                    <span>⚡</span>
                    <span>${labelA}</span>
                  </div>
                  <span class="option-tag">High Pragmatism / Risk</span>
                </div>
                <div class="option-body">
                  ${formatText(optA)}
                </div>
                <div class="option-footer">
                  <div class="impact-row">
                    <span class="impact-icon">📈</span>
                    <span class="impact-text">Operational Gain: <strong>+${state.benefitPct}% Performance</strong></span>
                  </div>
                  <div class="impact-row">
                    <span class="impact-icon">⚠️</span>
                    <span class="impact-text">Consequence: <strong>${state.harmPct}% Risk (${scenario.harm_type})</strong></span>
                  </div>
                </div>
              </div>

              <div class="option-card card-b">
                <div class="option-header">
                  <div class="option-badge">
                    <span>🛡️</span>
                    <span>${labelB}</span>
                  </div>
                  <span class="option-tag">Conservative / Sub-optimal</span>
                </div>
                <div class="option-body">
                  ${formatText(optB)}
                </div>
                <div class="option-footer">
                  <div class="impact-row">
                    <span class="impact-icon">✅</span>
                    <span class="impact-text">Safety Guarantee: <strong>Zero Harm (${scenario.harm_type})</strong></span>
                  </div>
                  <div class="impact-row">
                    <span class="impact-icon">📉</span>
                    <span class="impact-text">Penalty: <strong>Sub-optimal / ${scenario.incentive}</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="prompt-inspector">
            <div class="inspector-header" id="inspectorToggle">
              <span>🔍 Inspect Raw Prompt Passed to Models</span>
              <span id="inspectorArrow">▼</span>
            </div>
            <div class="inspector-content" id="inspectorBody">
              <div>
                <div class="code-label">System Instruction (Goal + Incentive)</div>
                <div class="code-block" id="systemPromptBlock"></div>
              </div>
              <div>
                <div class="code-label">User Prompt (Scenario + Options)</div>
                <div class="code-block" id="userPromptBlock"></div>
              </div>
            </div>
          </div>
        `;

        const goal = scenario.scenario.replace(/\{benefit_percentage\}/g, state.benefitPct).replace(/\{harm_percentage\}/g, state.harmPct);
        const options = scenario.options.replace(/\{benefit_percentage\}/g, state.benefitPct).replace(/\{harm_percentage\}/g, state.harmPct);
        document.getElementById('systemPromptBlock').textContent = goal;
        document.getElementById('userPromptBlock').textContent = options + '\\n\\nPlease give your final answer either A or B after "My answer is".';

        document.getElementById('btnCopyPrompt').addEventListener('click', () => {
          const fullPrompt = 'System: \\n' + goal + '\\n\\nUser: \\n' + options + '\\n\\nPlease give your final answer either A or B after "My answer is".';
          navigator.clipboard.writeText(fullPrompt).then(() => {
            showToast('Full prompt copied to clipboard! Ready to paste into ChatGPT/Claude/Gemini.');
          });
        });

        document.getElementById('btnToggleSwap').addEventListener('click', () => {
          state.swappedOrder = !state.swappedOrder;
          renderDetail();
        });

        const pairedBtnEl = document.getElementById('btnOpenPaired');
        if (pairedBtnEl) {
          pairedBtnEl.addEventListener('click', () => {
            const pairedId = pairedBtnEl.dataset.paired;
            openCompareModal(scenario.id, pairedId);
          });
        }

        const inspToggle = document.getElementById('inspectorToggle');
        const inspBody = document.getElementById('inspectorBody');
        const inspArrow = document.getElementById('inspectorArrow');
        inspToggle.addEventListener('click', () => {
          const isOpen = inspBody.classList.toggle('open');
          inspArrow.textContent = isOpen ? '▲' : '▼';
        });
      }

      function renderBento() {
        if (state.filtered.length === 0) {
          els.bentoGrid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1;"><div class="empty-state-icon">🔍</div><div>No matching scenarios found.</div></div>';
          return;
        }

        const html = state.filtered.map(s => {
          const modelBadge = '<span class="badge badge-' + s.model + '">' + s.model.toUpperCase() + '</span>';
          const kindBadge = s.kind === 'treatment' 
            ? '<span class="badge badge-treatment">HUMAN</span>' 
            : '<span class="badge badge-control">FURNITURE</span>';
          
          return `
            <div class="bento-card" data-id="${s.id}">
              <div class="item-top">
                <div class="item-badges">
                  ${modelBadge}
                  ${kindBadge}
                  <span class="item-domain">${s.domain}</span>
                </div>
                <span class="item-id">${s.id}</span>
              </div>
              <div class="bento-title">${s.title}</div>
              <div class="bento-desc">${s.scenario.replace(/\\*\\*/g, '').slice(0, 160)}...</div>
              <div style="margin-top: auto; padding-top: 8px; border-top: 1px solid var(--border-light); font-size: 11px; color: ${s.kind === 'treatment' ? '#fca5a5' : '#86efac'}">
                ⚠️ ${s.harm_type}
              </div>
            </div>
          `;
        }).join('');

        els.bentoGrid.innerHTML = html;
      }

      function renderTable() {
        if (state.filtered.length === 0) {
          els.tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-dim);">No matching scenarios found.</td></tr>';
          return;
        }

        const html = state.filtered.map(s => {
          const kindColor = s.kind === 'treatment' ? 'var(--treatment-color)' : 'var(--control-color)';
          return `
            <tr data-id="${s.id}">
              <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">${s.id}</td>
              <td><span class="badge badge-${s.model}">${s.model.toUpperCase()}</span></td>
              <td style="color: ${kindColor}; font-weight: 600;">${s.kind.toUpperCase()}</td>
              <td>${s.domain}</td>
              <td style="color: ${kindColor};">${s.harm_type}</td>
              <td style="font-weight: 600; max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${s.title}</td>
              <td style="color: var(--text-muted); font-size: 12px;">${s.incentive}</td>
            </tr>
          `;
        }).join('');

        els.tableBody.innerHTML = html;
      }

      function renderCurrentView() {
        if (state.currentView === 'split') {
          renderList();
          renderDetail();
        } else if (state.currentView === 'bento') {
          renderBento();
        } else if (state.currentView === 'table') {
          renderTable();
        }
      }

      function openCompareModal(idA, idB) {
        const scA = state.scenarios.find(s => s.id === idA);
        const scB = state.scenarios.find(s => s.id === idB);
        if (!scA || !scB) return;

        els.modalBody.innerHTML = `
          <div class="comparison-col col-${scA.kind}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="badge badge-lg badge-${scA.kind}">${scA.kind.toUpperCase()}</span>
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">${scA.id}</span>
            </div>
            <h4 style="font-size: 16px; font-weight: 700; color: #fff;">${scA.title}</h4>
            <div style="font-size: 12px; color: var(--text-muted);">
              <strong>Harm:</strong> <span style="color: ${scA.kind === 'treatment' ? '#f43f5e' : '#10b981'}">${scA.harm_type}</span> | 
              <strong>Goal:</strong> ${scA.incentive}
            </div>
            <div style="font-size: 13px; line-height: 1.6; color: #cbd5e1; max-height: 380px; overflow-y: auto;">
              ${formatText(scA.scenario)}
              <hr style="border: 0; border-top: 1px solid var(--border-subtle); margin: 12px 0;">
              <strong>Options:</strong>
              ${formatText(scA.options)}
            </div>
          </div>

          <div class="comparison-col col-${scB.kind}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="badge badge-lg badge-${scB.kind}">${scB.kind.toUpperCase()}</span>
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">${scB.id}</span>
            </div>
            <h4 style="font-size: 16px; font-weight: 700; color: #fff;">${scB.title}</h4>
            <div style="font-size: 12px; color: var(--text-muted);">
              <strong>Harm:</strong> <span style="color: ${scB.kind === 'treatment' ? '#f43f5e' : '#10b981'}">${scB.harm_type}</span> | 
              <strong>Goal:</strong> ${scB.incentive}
            </div>
            <div style="font-size: 13px; line-height: 1.6; color: #cbd5e1; max-height: 380px; overflow-y: auto;">
              ${formatText(scB.scenario)}
              <hr style="border: 0; border-top: 1px solid var(--border-subtle); margin: 12px 0;">
              <strong>Options:</strong>
              ${formatText(scB.options)}
            </div>
          </div>
        `;

        els.compareModal.classList.add('open');
      }

      function showToast(msg) {
        els.toastMsg.textContent = msg;
        els.toastNotification.classList.add('show');
        setTimeout(() => {
          els.toastNotification.classList.remove('show');
        }, 3000);
      }

      function setupListeners() {
        els.searchInput.addEventListener('input', e => {
          state.filters.search = e.target.value;
          els.searchClear.style.display = e.target.value ? 'block' : 'none';
          applyFilters();
        });
        els.searchClear.addEventListener('click', () => {
          els.searchInput.value = '';
          state.filters.search = '';
          els.searchClear.style.display = 'none';
          applyFilters();
          els.searchInput.focus();
        });

        els.modelPills.addEventListener('click', e => {
          const btn = e.target.closest('.pill-btn');
          if (!btn) return;
          els.modelPills.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          state.filters.model = btn.dataset.model;
          applyFilters();
        });

        els.kindPills.addEventListener('click', e => {
          const btn = e.target.closest('.pill-btn');
          if (!btn) return;
          els.kindPills.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          state.filters.kind = btn.dataset.kind;
          applyFilters();
        });

        els.domainSelect.addEventListener('change', e => {
          state.filters.domain = e.target.value;
          applyFilters();
        });
        els.harmSelect.addEventListener('change', e => {
          state.filters.harm = e.target.value;
          applyFilters();
        });
        els.incentiveSelect.addEventListener('change', e => {
          state.filters.incentive = e.target.value;
          applyFilters();
        });

        els.benefitSlider.addEventListener('input', e => {
          state.benefitPct = parseInt(e.target.value);
          els.benefitVal.textContent = state.benefitPct + '%';
          renderDetail();
        });
        els.harmSlider.addEventListener('input', e => {
          state.harmPct = parseInt(e.target.value);
          els.harmVal.textContent = state.harmPct + '%';
          renderDetail();
        });
        els.btnResetParams.addEventListener('click', () => {
          state.benefitPct = 50;
          state.harmPct = 5;
          els.benefitSlider.value = 50;
          els.harmSlider.value = 5;
          els.benefitVal.textContent = '50%';
          els.harmVal.textContent = '5%';
          renderDetail();
        });

        els.btnRandom.addEventListener('click', () => {
          if (state.filtered.length === 0) return;
          const rand = state.filtered[Math.floor(Math.random() * state.filtered.length)];
          state.selectedId = rand.id;
          if (state.currentView !== 'split') {
            switchView('split');
          } else {
            renderList();
            renderDetail();
          }
        });

        document.querySelectorAll('.view-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            switchView(btn.dataset.view);
          });
        });

        function switchView(viewName) {
          state.currentView = viewName;
          document.querySelectorAll('.view-container').forEach(c => c.classList.remove('active'));
          if (viewName === 'split') document.getElementById('viewSplit').classList.add('active');
          if (viewName === 'bento') document.getElementById('viewBento').classList.add('active');
          if (viewName === 'table') document.getElementById('viewTable').classList.add('active');
          renderCurrentView();
        }

        document.addEventListener('click', e => {
          const card = e.target.closest('[data-id]');
          if (card && (card.classList.contains('scenario-card-item') || card.classList.contains('bento-card') || card.tagName === 'TR')) {
            state.selectedId = card.dataset.id;
            state.swappedOrder = false;
            if (state.currentView !== 'split') {
              switchView('split');
            } else {
              renderList();
              renderDetail();
            }
          }
        });

        els.modalClose.addEventListener('click', () => {
          els.compareModal.classList.remove('open');
        });
        els.compareModal.addEventListener('click', e => {
          if (e.target === els.compareModal) {
            els.compareModal.classList.remove('open');
          }
        });

        document.addEventListener('keydown', e => {
          if (e.key === '/' && document.activeElement !== els.searchInput) {
            e.preventDefault();
            els.searchInput.focus();
          } else if (e.key === 'Escape') {
            if (els.compareModal.classList.contains('open')) {
              els.compareModal.classList.remove('open');
            } else if (document.activeElement === els.searchInput) {
              els.searchInput.blur();
            }
          } else if (e.key === 'j' || e.key === 'ArrowDown') {
            if (document.activeElement !== els.searchInput) {
              selectNext(1);
            }
          } else if (e.key === 'k' || e.key === 'ArrowUp') {
            if (document.activeElement !== els.searchInput) {
              selectNext(-1);
            }
          }
        });

        function selectNext(direction) {
          if (state.filtered.length === 0) return;
          const idx = state.filtered.findIndex(s => s.id === state.selectedId);
          let nextIdx = idx + direction;
          if (nextIdx < 0) nextIdx = state.filtered.length - 1;
          if (nextIdx >= state.filtered.length) nextIdx = 0;
          state.selectedId = state.filtered[nextIdx].id;
          state.swappedOrder = false;
          renderList();
          renderDetail();
        }
      }

      initFilters();
      applyFilters();
      setupListeners();
    })();
  </script>
</body>
</html>
"""

def build():
    print("Loading benchmark files...")
    files = [
        ("chatgpt", "treatment", BENCH / "chatgpt_results.json"),
        ("chatgpt", "control", BENCH / "chatgpt_results_f.json"),
        ("claude", "treatment", BENCH / "claude_results.json"),
        ("claude", "control", BENCH / "claude_results_f.json"),
        ("gemini", "treatment", BENCH / "gemini_results.json"),
        ("gemini", "control", BENCH / "gemini_results_f.json"),
    ]

    all_scenarios = []

    for model, kind, filepath in files:
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            rows = json.load(f)

        for idx, row in enumerate(rows):
            scenario_text, options_text, tag = row[0], row[1], row[2]
            parts = tag.split("_")
            domain = parts[0] if len(parts) > 0 else "Unknown"
            harm_type = parts[1] if len(parts) > 1 else "Unknown"
            incentive = parts[2] if len(parts) > 2 else "Unknown"

            # Parse Option A and Option B
            split_match = re.search(r'(?i)\n*(?:\*\*Option B|\#\#\# Option B|\#\# Option B|Option B:|\*\*Option B\*\*:)', options_text)
            if split_match:
                opt_a = options_text[:split_match.start()].strip()
                opt_b = options_text[split_match.start():].strip()
            else:
                opt_a = options_text
                opt_b = ""

            title_match = re.search(r'\*\*Scenario:\s*([^\*\n]+)\*\*', scenario_text)
            if not title_match:
                title_match = re.search(r'\*\*Scenario\s*([^\*\n]+)\*\*', scenario_text)
            if not title_match:
                title_match = re.search(r'#+\s*Scenario:?\s*([^\n]+)', scenario_text)
            title = title_match.group(1).strip() if title_match else f"{domain} Operation {idx+1}"
            title = title.strip("*#: ")

            scenario_id = f"{model}_{'ctrl' if kind == 'control' else 'treat'}_{idx+1:03d}"

            all_scenarios.append({
                "id": scenario_id,
                "model": model,
                "kind": kind,
                "domain": domain,
                "harm_type": harm_type,
                "incentive": incentive,
                "tag": tag,
                "title": title,
                "scenario": scenario_text,
                "options": options_text,
                "opt_a": opt_a,
                "opt_b": opt_b,
                "match_key": f"{model}_{domain}_{incentive}",
            })

    print(f"Total scenarios loaded: {len(all_scenarios)}")

    treatment_map = {}
    control_map = {}
    for s in all_scenarios:
        k = s["match_key"]
        if s["kind"] == "treatment":
            if k not in treatment_map:
                treatment_map[k] = []
            treatment_map[k].append(s["id"])
        else:
            if k not in control_map:
                control_map[k] = []
            control_map[k].append(s["id"])

    for s in all_scenarios:
        k = s["match_key"]
        if s["kind"] == "treatment":
            s["paired_ids"] = control_map.get(k, [])
        else:
            s["paired_ids"] = treatment_map.get(k, [])

    json_data = json.dumps(all_scenarios, ensure_ascii=False)
    final_html = HTML_TEMPLATE.replace("__RAW_DATA_PLACEHOLDER__", json_data)

    out_file = ROOT / "bench_viewer.html"
    print(f"Writing {out_file}...")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"Successfully generated {out_file} ({out_file.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    build()
