<script lang="ts">
	import { marked } from 'marked'
	import DOMPurify from 'dompurify'

	type Props = {
		content: string
		variant: 'user' | 'assistant'
	}

	let { content, variant }: Props = $props()

	function renderMarkdown(text: string): string {
		const html = marked.parse(text, { async: false }) as string
		return DOMPurify.sanitize(html)
	}
</script>

<div class="message-body {variant}">
	{@html renderMarkdown(content)}
</div>

<style>
	.message-body {
		font-size: 0.875rem;
		line-height: 1.5;
	}

	/* Remove margin from first/last elements */
	.message-body :global(> *:first-child) {
		margin-top: 0;
	}
	.message-body :global(> *:last-child) {
		margin-bottom: 0;
	}

	/* Headings */
	.message-body :global(h1) {
		font-size: 1.5em;
		font-weight: 700;
		margin: 0.75em 0 0.5em;
	}
	.message-body :global(h2) {
		font-size: 1.25em;
		font-weight: 600;
		margin: 0.75em 0 0.5em;
	}
	.message-body :global(h3) {
		font-size: 1.1em;
		font-weight: 600;
		margin: 0.5em 0 0.25em;
	}

	/* Paragraphs */
	.message-body :global(p) {
		margin: 0.5em 0;
	}

	/* Lists */
	.message-body :global(ul) {
		list-style-type: disc;
		padding-left: 1.5em;
		margin: 0.5em 0;
	}
	.message-body :global(ol) {
		list-style-type: decimal;
		padding-left: 1.5em;
		margin: 0.5em 0;
	}
	.message-body :global(li) {
		margin: 0.25em 0;
	}
	.message-body :global(li > ul),
	.message-body :global(li > ol) {
		margin: 0.25em 0;
	}

	/* Code */
	.message-body :global(code) {
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace;
		font-size: 0.85em;
		padding: 0.15em 0.35em;
		border-radius: 0.25em;
	}

	/* Code blocks */
	.message-body :global(pre) {
		margin: 0.75em 0;
		padding: 0.75em 1em;
		border-radius: 0.5em;
		overflow-x: auto;
	}
	.message-body.user :global(pre) {
		background-color: #f1f5f9;
	}
	.message-body.assistant :global(pre) {
		background-color: rgba(0, 0, 0, 0.3);
	}
	.message-body :global(pre code) {
		padding: 0;
		background: transparent;
		font-size: 0.8em;
	}

	/* Blockquotes */
	.message-body :global(blockquote) {
		margin: 0.75em 0;
		padding: 0.5em 1em;
		border-left: 3px solid;
		font-style: italic;
	}
	.message-body.user :global(blockquote) {
		border-color: #818cf8;
		background-color: #f1f5f9;
	}
	.message-body.assistant :global(blockquote) {
		border-color: #94a3b8;
		background-color: rgba(255, 255, 255, 0.05);
	}

	/* Links */
	.message-body :global(a) {
		text-decoration: underline;
	}
	.message-body.user :global(a) {
		color: #4f46e5;
	}
	.message-body.assistant :global(a) {
		color: #a5b4fc;
	}

	/* Strong and emphasis */
	.message-body :global(strong) {
		font-weight: 600;
	}
	.message-body :global(em) {
		font-style: italic;
	}

	/* Horizontal rule */
	.message-body :global(hr) {
		margin: 1em 0;
		border: none;
		border-top: 1px solid;
	}
	.message-body.user :global(hr) {
		border-color: #cbd5e1;
	}
	.message-body.assistant :global(hr) {
		border-color: rgba(255, 255, 255, 0.2);
	}

	/* Tables */
	.message-body :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: 0.75em 0;
		font-size: 0.9em;
	}
	.message-body :global(th),
	.message-body :global(td) {
		padding: 0.5em 0.75em;
		text-align: left;
		border: 1px solid;
	}
	.message-body.user :global(th),
	.message-body.user :global(td) {
		border-color: #cbd5e1;
	}
	.message-body.assistant :global(th),
	.message-body.assistant :global(td) {
		border-color: rgba(255, 255, 255, 0.2);
	}
	.message-body :global(th) {
		font-weight: 600;
	}
	.message-body.user :global(th) {
		background-color: #f1f5f9;
	}
	.message-body.assistant :global(th) {
		background-color: rgba(255, 255, 255, 0.05);
	}
</style>
