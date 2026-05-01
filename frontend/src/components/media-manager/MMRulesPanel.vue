<template>
  <div class="mm-config-body">
    <p class="mm-desc">{{ $t('mediaManager.customRulesDesc') }}</p>
    <div class="mm-example-block">
      <div class="mm-example-title">{{ $t('mediaManager.customRulesExamplesTitle') }}</div>
      <div class="mm-example-lines">
        <span>HDLight → <span class="mm-txt-green">1080p</span></span>
        <span>MULTI → <span class="mm-txt-green">(vide)</span></span>
        <span>\.FRENCH\. → <span class="mm-txt-green">.</span> <span class="mm-txt-muted">(regex)</span></span>
      </div>
    </div>
    <div class="mm-rules-list">
      <div v-for="rule in customRules" :key="rule.id" class="mm-rule-row mm-rule-row-horiz">
        <input v-model="rule.enabled" type="checkbox" class="mm-chkbox" @change="saveRulesChange"/>
        <div class="mm-rule-text">
          <div class="mm-rule-label mm-mono">{{ rule.from }} → {{ rule.to }}</div>
          <div class="mm-rule-hint">{{ rule.type === RULE_TYPE.REGEX ? 'Regex' : 'Texte' }}{{ rule.flags ? ' · flags: ' + rule.flags : '' }}</div>
        </div>
        <button class="mm-btn-sm mm-rule-del" @click="deleteCustomRule(rule.id)">✕</button>
      </div>
      <div v-if="!customRules.length" class="mm-state mm-state-pad"><span class="mm-state-text">{{ $t('mediaManager.noRules') }}</span></div>
    </div>
    <hr class="mm-divider"/>
    <div class="mm-label">{{ $t('mediaManager.addRule') }}</div>
    <div class="mm-add-grid">
      <input v-model="newRule.from" class="mm-folder-input mm-input-flat" :placeholder="$t('common.search')"/>
      <input v-model="newRule.to" class="mm-folder-input mm-input-flat" :placeholder="''"/>
      <button class="mm-btn-sm mm-btn-success" @click="addRuleLocal">+</button>
    </div>
    <div class="mm-regex-row">
      <label class="mm-regex-label">
        <input v-model="newRule.isRegex" type="checkbox" class="mm-chkbox"/> {{ $t('mediaManager.regexLabel') }}
      </label>
      <input v-if="newRule.isRegex" v-model="newRule.flags" class="mm-folder-input mm-input-flat mm-flags-input" placeholder="gi"/>
    </div>
  </div>
</template>

<script setup>
import { useMediaManager } from '@/composables/useMediaManager'
import { useMMConfigPanels } from '@/composables/useMMConfigPanels'
import { RULE_TYPE } from '@/constants/mediaManager'

const { customRules, deleteCustomRule } = useMediaManager()
const { newRule, addRuleLocal, saveRulesChange } = useMMConfigPanels()
</script>

<style scoped>
/* Section description (appears above the examples block) */
.mm-desc { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: .5rem; }
/* Examples block: a small card showing rule before/after */
.mm-example-block { font-size: var(--text-2xs); color: var(--text-muted); margin-bottom: .75rem; padding: .4rem .6rem; background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-sm); }
.mm-example-title { font-weight: var(--font-medium); margin-bottom: .25rem; }
.mm-example-lines { font-family: monospace; font-size: var(--text-3xs); display: flex; flex-direction: column; gap: .15rem; }
/* Inline colour helpers */
.mm-txt-green { color: var(--mm-green); }
.mm-txt-muted { color: var(--text-muted); }
/* Monospace text label */
.mm-mono { font-family: monospace; }
/* Stacked list of rules */
.mm-rules-list { display: flex; flex-direction: column; gap: .4rem; margin-bottom: .6rem; }
.mm-rule-row-horiz { flex-direction: row; }
.mm-rule-text { flex: 1; min-width: 0; }
.mm-rule-del { color: var(--mm-red); flex-shrink: 0; }
/* Empty-state message */
.mm-state-pad { padding: .5rem; }
.mm-state-text { font-size: var(--text-xs); }
/* Divider between list and "add rule" form */
.mm-divider { border-color: var(--border); margin: .6rem 0; }
/* Add-rule form grid */
.mm-add-grid { display: grid; grid-template-columns: 1fr 1fr auto; gap: .4rem; margin-top: .4rem; }
.mm-input-flat { margin-top: 0; }
/* Regex toggle row */
.mm-regex-row { display: flex; align-items: center; gap: .5rem; margin-top: .35rem; }
.mm-regex-label { display: flex; align-items: center; gap: .3rem; font-size: var(--text-2xs); color: var(--text-muted); }
.mm-flags-input { width: 70px; }
</style>
