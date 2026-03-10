class MarkdownParser {
    constructor() {
        this.codeBlocks = [];
    }

    parse(text) {
        if (!text) return '';
        
        this.codeBlocks = [];
        
        let html = text;
        
        html = this._extractCodeBlocks(html);
        html = this._escapeHtmlButKeepTables(html);
        html = this._restoreCodeBlocks(html);
        html = this._parseHeaders(html);
        html = this._parseBold(html);
        html = this._parseItalic(html);
        html = this._parseInlineCode(html);
        html = this._parseLinks(html);
        html = this._parseLists(html);
        html = this._parseParagraphs(html);
        html = this._parseBlockquotes(html);
        html = this._parseHorizontalRules(html);
        
        return html;
    }

    _extractCodeBlocks(html) {
        return html.replace(/```([\s\S]*?)```/g, (match, code) => {
            const index = this.codeBlocks.length;
            this.codeBlocks.push(`<pre><code>${this._escapeHtml(code.trim())}</code></pre>`);
            return `%%CODEBLOCK_${index}%%`;
        });
    }

    _restoreCodeBlocks(html) {
        return html.replace(/%%CODEBLOCK_(\d+)%%/g, (match, index) => {
            return this.codeBlocks[index] || match;
        });
    }

    _escapeHtmlButKeepTables(text) {
        let result = '';
        let i = 0;
        
        while (i < text.length) {
            if (text.substr(i, 7) === '<table>') {
                let tableEnd = text.indexOf('</table>', i);
                if (tableEnd !== -1) {
                    result += text.substr(i, tableEnd - i + 8);
                    i = tableEnd + 8;
                    continue;
                }
            }
            
            if (text.substr(i, 5) === '<tr>' || text.substr(i, 6) === '<thead' || text.substr(i, 6) === '<tbody' || text.substr(i, 4) === '<th>' || text.substr(i, 4) === '<td>') {
                let tagEnd = text.indexOf('>', i);
                if (tagEnd !== -1) {
                    let nextClose = this._findMatchingTag(text, i);
                    if (nextClose !== -1) {
                        result += text.substr(i, nextClose - i + text.substr(nextClose).indexOf('>') + 1);
                        i = nextClose + text.substr(nextClose).indexOf('>') + 1;
                        continue;
                    }
                }
            }
            
            if (text[i] === '&') {
                result += '&amp;';
            } else if (text[i] === '<') {
                result += '&lt;';
            } else if (text[i] === '>') {
                result += '&gt;';
            } else {
                result += text[i];
            }
            i++;
        }
        
        return result;
    }

    _findMatchingTag(text, startPos) {
        const openTag = text.substr(startPos).match(/^<(\/?)(\w+)/);
        if (!openTag) return -1;
        
        const tagName = openTag[2].toLowerCase();
        let pos = startPos + openTag[0].length;
        let depth = 1;
        
        while (pos < text.length && depth > 0) {
            if (text.substr(pos, 2) === '</') {
                let closeEnd = text.indexOf('>', pos);
                if (closeEnd !== -1) {
                    let closeTag = text.substr(pos + 2, closeEnd - pos - 2).toLowerCase().trim();
                    if (closeTag === tagName) {
                        depth--;
                        if (depth === 0) return pos;
                    }
                    pos = closeEnd + 1;
                    continue;
                }
            }
            
            if (text[pos] === '<' && text[pos + 1] !== '/') {
                let tagEnd = text.indexOf('>', pos);
                if (tagEnd !== -1) {
                    let tagMatch = text.substr(pos).match(/^<(\w+)/);
                    if (tagMatch && tagMatch[1].toLowerCase() === tagName) {
                        depth++;
                    }
                    pos = tagEnd + 1;
                    continue;
                }
            }
            
            pos++;
        }
        
        return -1;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _parseHeaders(html) {
        return html
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>');
    }

    _parseBold(html) {
        return html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    _parseItalic(html) {
        return html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    _parseInlineCode(html) {
        return html.replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    _parseLinks(html) {
        return html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }

    _parseLists(html) {
        let lines = html.split('\n');
        let result = [];
        let inUnorderedList = false;
        let inOrderedList = false;
        
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            let unorderedMatch = line.match(/^\s*[-*+]\s+(.+)$/);
            let orderedMatch = line.match(/^\s*\d+\.\s+(.+)$/);
            
            if (unorderedMatch) {
                if (inOrderedList) {
                    result.push('</ol>');
                    inOrderedList = false;
                }
                if (!inUnorderedList) {
                    result.push('<ul>');
                    inUnorderedList = true;
                }
                result.push(`<li>${unorderedMatch[1]}</li>`);
            } else if (orderedMatch) {
                if (inUnorderedList) {
                    result.push('</ul>');
                    inUnorderedList = false;
                }
                if (!inOrderedList) {
                    result.push('<ol>');
                    inOrderedList = true;
                }
                result.push(`<li>${orderedMatch[1]}</li>`);
            } else {
                if (inUnorderedList) {
                    result.push('</ul>');
                    inUnorderedList = false;
                }
                if (inOrderedList) {
                    result.push('</ol>');
                    inOrderedList = false;
                }
                if (line.trim()) {
                    result.push(line);
                }
            }
        }
        
        if (inUnorderedList) result.push('</ul>');
        if (inOrderedList) result.push('</ol>');
        
        return result.join('\n');
    }

    _parseParagraphs(html) {
        let lines = html.split('\n\n');
        return lines.map(line => {
            line = line.trim();
            if (!line) return '';
            if (line.startsWith('<h') || line.startsWith('<ul') || line.startsWith('<ol') || line.startsWith('<li') || line.startsWith('<pre') || line.startsWith('<table') || line.startsWith('<blockquote')) {
                return line;
            }
            return `<p>${line}</p>`;
        }).join('\n');
    }

    _parseBlockquotes(html) {
        return html.replace(/^&gt;\s*(.+)$/gim, '<blockquote>$1</blockquote>');
    }

    _parseHorizontalRules(html) {
        return html.replace(/^---$/gim, '<hr>');
    }
}

const markdownParser = new MarkdownParser();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarkdownParser;
}