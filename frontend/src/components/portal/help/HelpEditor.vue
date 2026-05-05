<template>
  <div class="pt-help-editor">
    <div v-if="editor" class="pt-help-editor-toolbar">
      <!-- Headings -->
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('heading', { level: 2 }) }"
        :title="$t('portal.help.editor.h2')"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        <Heading2 :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('heading', { level: 3 }) }"
        :title="$t('portal.help.editor.h3')"
        @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
      >
        <Heading3 :size="16" />
      </button>

      <span class="pt-help-tb-sep" />

      <!-- Inline marks -->
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('bold') }"
        :title="$t('portal.help.editor.bold')"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <Bold :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('italic') }"
        :title="$t('portal.help.editor.italic')"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <Italic :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('underline') }"
        :title="$t('portal.help.editor.underline')"
        @click="editor.chain().focus().toggleUnderline().run()"
      >
        <UnderlineIcon :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('strike') }"
        :title="$t('portal.help.editor.strike')"
        @click="editor.chain().focus().toggleStrike().run()"
      >
        <Strikethrough :size="16" />
      </button>

      <span class="pt-help-tb-sep" />

      <!-- Highlight (palette) -->
      <div class="pt-help-tb-pop">
        <button
          type="button"
          class="pt-help-tb-btn"
          :class="{ active: editor.isActive('highlight') }"
          :title="$t('portal.help.editor.highlight')"
        >
          <Highlighter :size="16" />
        </button>
        <div class="pt-help-tb-palette">
          <button
            v-for="c in HIGHLIGHT_COLORS"
            :key="c"
            class="pt-help-tb-swatch"
            :style="{ background: c }"
            type="button"
            @click="editor.chain().focus().toggleHighlight({ color: c }).run()"
          />
          <button
            class="pt-help-tb-swatch pt-help-tb-swatch--clear"
            type="button"
            @click="editor.chain().focus().unsetHighlight().run()"
          >
            ×
          </button>
        </div>
      </div>

      <!-- Text colour (palette) -->
      <div class="pt-help-tb-pop">
        <button
          type="button"
          class="pt-help-tb-btn"
          :class="{ active: editor.isActive('textStyle', { color: /.*/ }) }"
          :title="$t('portal.help.editor.color')"
        >
          <Palette :size="16" />
        </button>
        <div class="pt-help-tb-palette">
          <button
            v-for="c in TEXT_COLORS"
            :key="c"
            class="pt-help-tb-swatch"
            :style="{ background: c }"
            type="button"
            @click="editor.chain().focus().setColor(c).run()"
          />
          <button
            class="pt-help-tb-swatch pt-help-tb-swatch--clear"
            type="button"
            @click="editor.chain().focus().unsetColor().run()"
          >
            ×
          </button>
        </div>
      </div>

      <!-- Font size -->
      <select
        class="pt-help-tb-select"
        :title="$t('portal.help.editor.size')"
        @change="setFontSize($event.target.value)"
      >
        <option value="">{{ $t('portal.help.editor.sizeDefault') }}</option>
        <option value="0.875em">{{ $t('portal.help.editor.sizeS') }}</option>
        <option value="1.125em">{{ $t('portal.help.editor.sizeM') }}</option>
        <option value="1.35em">{{ $t('portal.help.editor.sizeL') }}</option>
        <option value="1.65em">{{ $t('portal.help.editor.sizeXL') }}</option>
      </select>

      <span class="pt-help-tb-sep" />

      <!-- Lists -->
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('bulletList') }"
        :title="$t('portal.help.editor.bulletList')"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        <List :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('orderedList') }"
        :title="$t('portal.help.editor.orderedList')"
        @click="editor.chain().focus().toggleOrderedList().run()"
      >
        <ListOrdered :size="16" />
      </button>

      <span class="pt-help-tb-sep" />

      <!-- Alignment -->
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive({ textAlign: 'left' }) }"
        :title="$t('portal.help.editor.alignLeft')"
        @click="editor.chain().focus().setTextAlign('left').run()"
      >
        <AlignLeft :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive({ textAlign: 'center' }) }"
        :title="$t('portal.help.editor.alignCenter')"
        @click="editor.chain().focus().setTextAlign('center').run()"
      >
        <AlignCenter :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive({ textAlign: 'right' }) }"
        :title="$t('portal.help.editor.alignRight')"
        @click="editor.chain().focus().setTextAlign('right').run()"
      >
        <AlignRight :size="16" />
      </button>

      <span class="pt-help-tb-sep" />

      <!-- Link / Quote / Table -->
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('link') }"
        :title="$t('portal.help.editor.link')"
        @click="setLink"
      >
        <LinkIcon :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :class="{ active: editor.isActive('blockquote') }"
        :title="$t('portal.help.editor.quote')"
        @click="editor.chain().focus().toggleBlockquote().run()"
      >
        <Quote :size="16" />
      </button>
      <button
        type="button"
        class="pt-help-tb-btn"
        :title="$t('portal.help.editor.table')"
        @click="editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
      >
        <TableIcon :size="16" />
      </button>
    </div>

    <EditorContent class="pt-help-editor-content" :editor="editor" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { Extension } from '@tiptap/core'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Highlighter,
  Palette,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Link as LinkIcon,
  Quote,
  Table as TableIcon,
} from 'lucide-vue-next'

import '@/assets/styles/portal/help-overlay-editor.css'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const TEXT_COLORS = [
  '#ffffff',
  '#cbd5e1',
  '#f87171',
  '#fb923c',
  '#facc15',
  '#4ade80',
  '#60a5fa',
  '#a78bfa',
]
const HIGHLIGHT_COLORS = ['#fde68a', '#fca5a5', '#bbf7d0', '#bfdbfe', '#ddd6fe']

// Inline font-size mark — not part of stock Tiptap, so a tiny extension
// reuses the textStyle node and stores ``font-size: ...`` on the <span>.
// The backend bleach pass already whitelists this CSS property.
const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() {
    return { types: ['textStyle'] }
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: el => el.style.fontSize || null,
            renderHTML: attrs => (attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {}),
          },
        },
      },
    ]
  },
})

// `isEmittingFromEditor` short-circuits the modelValue watcher when the
// HTML coming back from the parent originates from this editor's own
// `onUpdate`. Without it, TipTap's internal HTML serialisation may differ
// from what we just emitted (whitespace, attribute order…), the watcher
// then calls `setContent` and the caret jumps to the start mid-typing —
// which the user perceives as "my edit was reverted".
let isEmittingFromEditor = false

const editor = new Editor({
  content: props.modelValue || '',
  extensions: [
    StarterKit,
    Underline,
    TextStyle,
    Color,
    FontSize,
    Highlight.configure({ multicolor: true }),
    Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Table.configure({ resizable: true }),
    TableRow,
    TableCell,
    TableHeader,
  ],
  editorProps: { attributes: { class: 'pt-help-editor-prose' } },
  onUpdate: ({ editor: e }) => {
    isEmittingFromEditor = true
    emit('update:modelValue', e.getHTML())
  },
})

function setFontSize(value) {
  if (!value) editor.chain().focus().setMark('textStyle', { fontSize: null }).run()
  else editor.chain().focus().setMark('textStyle', { fontSize: value }).run()
}

function setLink() {
  const previous = editor.getAttributes('link').href
  // eslint-disable-next-line no-alert
  const url = window.prompt('URL', previous || 'https://')
  if (url === null) return
  if (url === '') {
    editor.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
}

watch(
  () => props.modelValue,
  next => {
    if (!editor) return
    if (isEmittingFromEditor) {
      isEmittingFromEditor = false
      return
    }
    if (editor.getHTML() === next) return
    editor.commands.setContent(next || '', false)
  },
)

onBeforeUnmount(() => editor?.destroy())
</script>

<!-- Styles externalised to assets/styles/portal/help-overlay-editor.css -->
