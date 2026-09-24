<template>
  <div class="poc-dialog-body hier-add">
    <!-- 当前节点上下文 -->
    <el-alert type="info" :closable="false" show-icon class="m-b-12">
      <template #title>
        <b>{{ modeTitle }}：</b>
        当前节点 {{ currentNode?.name ?? '—' }}（{{ currentNode?.oneId ?? '—' }} · {{ currentNode?.level ?? '—' }}）
        <template v-if="mode === 'child'">　→ 在其下新增 {{ nextLevelHint }} 级子节点</template>
        <template v-else-if="mode === 'edit'">　→ 修改它挂在谁下面（历史版本不会被覆盖）</template>
      </template>
    </el-alert>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="150px">
      <el-form-item v-if="mode === 'edit'" label="关系编码">
        <el-input :model-value="activeRelation?.relationCode ?? '—'" readonly />
      </el-form-item>

      <el-form-item label="父节点 One ID" prop="parentOneId">
        <!-- 🚨 request/manage 从页头进入时无 nodeKey，父节点必须可自选（只读空 input 是死局） -->
        <el-select
          v-if="mode !== 'child'"
          v-model="form.parentOneId"
          filterable
          placeholder="选择父节点（A3 / A2）"
          style="width: 100%"
        >
          <el-option
            v-for="item in parentCandidates"
            :key="item.oneId"
            :label="`${item.level} · ${item.name} · ${item.oneId}`"
            :value="item.oneId"
          />
        </el-select>
        <el-input v-else :model-value="form.parentOneId" readonly />
      </el-form-item>

      <el-form-item v-if="mode === 'edit'" label="当前父节点">
        <el-input :model-value="activeRelation?.parentOneId ?? '无'" readonly />
      </el-form-item>

      <el-form-item label="子节点 One ID" prop="childOneId">
        <!--
          子节点一律用「待归位主数据」下拉选择（request / manage / child 同一数据源），
          不给自由输入：One ID 是系统生成的编码，手输必然拼错且选不到未归位主数据；
          只有 edit（改挂）模式子节点固定不可改，保持只读。
        -->
        <el-select
          v-if="mode !== 'edit'"
          v-model="form.childOneId"
          filterable
          clearable
          placeholder="选择待归位主数据（已批准成为主数据）"
          style="width: 100%"
        >
          <el-option
            v-for="item in unassigned"
            :key="item.oneId"
            :label="`${item.name} · ${item.oneId} · 建议 ${item.suggestedLevel}`"
            :value="item.oneId"
          />
        </el-select>
        <el-input v-else :model-value="form.childOneId" readonly />
      </el-form-item>

      <!-- 关系类型由后端按父子级别实时推导（见下方校验区「推导关系」），不让用户手选一个会被系统覆盖的值 -->
      <el-form-item label="关系类型">
        <el-input :model-value="relationLabel" placeholder="选择父 / 子节点后自动推导" readonly />
      </el-form-item>

      <!-- 层级类型按子节点级别自动推导（总设计：A3→商业主体 / A2→法人 / A1→门店），挂载审批时系统同样按级别落库 -->
      <el-form-item label="层级类型">
        <el-input
          :model-value="derivedHierarchyType?.label ?? ''"
          placeholder="选择子节点后按级别自动推导"
          readonly
        />
      </el-form-item>

      <el-form-item label="Payer One ID">
        <el-input v-model="form.payerOneId" placeholder="选填 · 付款方 One ID（如 GC-PY-0091），A1 门店挂 Payer 时填写" />
      </el-form-item>

      <el-form-item label="生效日期" prop="effectiveFrom">
        <el-date-picker v-model="form.effectiveFrom" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>

      <el-form-item label="失效日期">
        <el-date-picker v-model="form.effectiveTo" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>

      <el-form-item label="变更原因" prop="changeReason">
        <el-input v-model="form.changeReason" placeholder="如 新门店归属确认 / 法人主体调整" />
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>

    <!-- 提交前校验：结论完全来自数据库，前端不做任何自行推算 -->
    <div class="hier-check">
      <div class="hier-check-head">
        <span class="hier-check-title">提交前校验（Loop Check · 实时读库）</span>
        <el-button size="small" :loading="checking" @click="runCheck">重新校验</el-button>
      </div>

      <el-descriptions :column="2" border size="small" class="m-b-8">
        <el-descriptions-item label="推导关系">{{ validate.relationType || '—' }}</el-descriptions-item>
        <el-descriptions-item label="级别推导">
          {{ validate.parentLevel || '—' }}（depth {{ validate.parentDepth || 0 }}） →
          {{ validate.childLevel || '—' }}（depth {{ validate.childDepth || 0 }}）
        </el-descriptions-item>
        <el-descriptions-item label="挂载后完整路径" :span="2">
          {{ validate.previewPathNames || validate.previewPath || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="子节点当前归属">
          <span v-if="validate.childMounted">
            已挂在 {{ validate.childCurrentParentOneId || '—' }}（{{ validate.childCurrentLevel || '—' }}）
          </span>
          <span v-else>尚未归位</span>
        </el-descriptions-item>
        <el-descriptions-item label="跨 BU 判定">
          <el-tag size="small" :type="validate.crossBu ? 'warning' : 'success'" effect="plain">
            {{ validate.crossBu ? '跨 BU · 需升级 GC Scope' : '同 BU · BU Data Steward 处理' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-table v-loading="checking" :data="validate.checks" border size="small" class="data-table">
        <el-table-column label="检测项" prop="label" min-width="150" />
        <el-table-column label="结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="dark"
              :type="row.checkResult === 'PASS' ? 'success' : row.checkResult === 'FAIL' ? 'danger' : 'warning'"
            >
              {{ row.checkResult }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结论" prop="message" min-width="280" show-overflow-tooltip />
        <el-table-column label="冲突路径 / 建议" min-width="220">
          <template #default="{ row }">
            <div v-if="row.conflictPath" class="hier-conflict">{{ row.conflictPath }}</div>
            <span v-else-if="row.suggestion">{{ row.suggestion }}</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        v-if="validate.checks.length"
        :type="validate.passed ? 'success' : 'error'"
        :closable="false"
        show-icon
        class="m-t-8"
      >
        <template #title>
          {{ validate.passed ? '校验通过，可提交' : `校验未通过 · BLOCKED：${validate.blockedReason || '存在阻塞项'}` }}
        </template>
      </el-alert>
      <el-empty v-else description="请先选择父节点与子节点，系统将实时校验并给出结论" :image-size="60" />
    </div>

    <!-- 关系历史：历史归属不覆盖 -->
    <template v-if="mode === 'edit'">
      <div class="hier-section-title">历史归属（改挂不覆盖历史版本）</div>
      <el-table :data="history" border size="small" class="data-table">
        <el-table-column label="版本" prop="versionNo" width="70" align="center" />
        <el-table-column label="操作" prop="operation" width="90" />
        <el-table-column label="父节点" prop="parentOneId" min-width="150" />
        <el-table-column label="状态" prop="status" width="100" />
        <el-table-column label="变更原因" prop="changeReason" min-width="160" show-overflow-tooltip />
        <el-table-column label="时间" prop="createTime" width="160" />
      </el-table>
      <el-empty v-if="!history.length" description="暂无历史版本" :image-size="50" />
    </template>

    <el-alert type="info" :closable="false" show-icon class="m-t-12">
      <template #title><b>审批流：</b>{{ flowText }}</template>
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import {
  addHierarchyChild,
  addHierarchyRelation,
  getHierarchy,
  getHierarchyNode,
  getHierarchyRelationHistory,
  getNodeActiveRelation,
  getUnassignedNodes,
  updateHierarchyRelation,
  validateHierarchyRelation
} from '@/api/demo/cmdPoc';
import type {
  HierarchyNodeVO,
  HierarchyRelationHistVO,
  HierarchyRelationVO,
  HierarchyUnassignedVO,
  HierarchyValidateVO
} from '@/api/demo/cmdPoc/types';
import { useCmdPoc } from '../../composables/useCmdPoc';

defineOptions({ name: 'CmdPocHierarchyAddDialog' });

type Mode = 'request' | 'manage' | 'child' | 'edit';

const props = defineProps<{ payload?: { mode?: string; nodeKey?: string } }>();

const { roleKey, markHierarchyChanged } = useCmdPoc();
const formRef = ref<FormInstance>();
const checking = ref(false);

const mode = computed<Mode>(() => (props.payload?.mode as Mode) || 'manage');
const nodeKey = computed(() => props.payload?.nodeKey || '');

/** 展示文案 → 后端关系类型枚举 */
const RELATION_CODE: Record<string, string> = {
  'A3 Commercial Entity → A2 Main Account': 'A3_A2',
  'A2 Main Account → A1 Door': 'A2_A1'
};

const currentNode = ref<HierarchyNodeVO | null>(null);
const unassigned = ref<HierarchyUnassignedVO[]>([]);
const parentCandidates = ref<HierarchyNodeVO[]>([]);
const activeRelation = ref<HierarchyRelationVO | null>(null);
const history = ref<HierarchyRelationHistVO[]>([]);

const form = reactive({
  hierarchyType: 'LEGAL',
  relationType: 'A2_A1',
  parentOneId: '',
  childOneId: '',
  payerOneId: '',
  effectiveFrom: new Date().toISOString().slice(0, 10),
  effectiveTo: '',
  changeReason: '',
  remark: ''
});

const emptyValidate = (): HierarchyValidateVO => ({
  checkCode: '',
  passed: false,
  relationLabel: '',
  parentName: '',
  childName: '',
  parentLevel: '',
  parentDepth: 0,
  childLevel: '',
  childDepth: 0,
  previewPath: '',
  previewPathNames: '',
  crossBu: false,
  requiresGcApproval: false,
  relationType: '',
  maxDepth: 3,
  childMounted: false,
  childCurrentParentOneId: '',
  childCurrentLevel: '',
  checks: [],
  executeTime: '',
  durationMs: 0
});

const validate = ref<HierarchyValidateVO>(emptyValidate());

const rules: FormRules = {
  parentOneId: [{ required: true, message: '请选择父节点', trigger: 'change' }],
  childOneId: [{ required: true, message: '请选择子节点', trigger: 'change' }],
  effectiveFrom: [{ required: true, message: '请选择生效日期', trigger: 'change' }],
  changeReason: [{ required: true, message: '请填写变更原因', trigger: 'blur' }]
};

const modeTitle = computed(() =>
  mode.value === 'request' ? '发起层级关系申请' : mode.value === 'edit' ? '编辑层级关系' : mode.value === 'child' ? '增加子节点' : '新增层级关系'
);

/** 关系类型展示文案：form.relationType 存后端推导的枚举码（A3_A2 / A2_A1），反查成中文 */
const relationLabel = computed(() => {
  if (!form.relationType) return '';
  const hit = Object.entries(RELATION_CODE).find(([, code]) => code === form.relationType);
  return hit?.[0] ?? form.relationType;
});

/** 子节点级别 → 层级类型（与后端 _hier_type_by_level 同口径：A3→COMMERCIAL / A2→LEGAL / A1→DOOR） */
const LEVEL_HIER_TYPE: Record<string, { code: string; label: string }> = {
  A3: { code: 'COMMERCIAL', label: 'Commercial · 商业主体（A3）' },
  A2: { code: 'LEGAL', label: 'Legal · 法人（A2）' },
  A1: { code: 'DOOR', label: 'Door · 门店（A1）' }
};

/** 子节点级别：优先取后端校验返回的「挂载后级别」（级别由挂载位置推导，父 depth+1），
 *  未校验时回落待归位主数据的建议级别 / 当前节点级别——与提交后系统落库口径一致 */
const childLevel = computed(() => {
  if (validate.value.childLevel) return validate.value.childLevel;
  return unassigned.value.find(item => item.oneId === form.childOneId)?.suggestedLevel ?? currentNode.value?.level ?? '';
});
const derivedHierarchyType = computed(() => LEVEL_HIER_TYPE[childLevel.value] ?? null);

const nextLevelHint = computed(() => {
  const depth = currentNode.value?.depth ?? 0;
  return depth >= 3 ? '（当前节点已是末端，不可再挂下级）' : depth === 1 ? 'A2' : 'A1';
});

const flowText = computed(() => {
  if (validate.value.requiresGcApproval) {
    return '跨 BU 关系：BU 提交 → 自动升级 GC Scope 审批 → 通过后发布并写入审计日志。';
  }
  if (mode.value === 'request') {
    return 'Business User 提交 → BU Data Steward 审核 → 通过后发布；如为跨 BU 关系则升级 GC Scope。';
  }
  if (roleKey.value === 'gc') {
    return 'GC Scope 审核跨 BU / 重大 A2、A3 关系 → 发布 → 审计记录。';
  }
  return 'BU Data Steward 处理本 BU 关系；跨 BU 或重大 A2/A3 关系升级 GC Scope。';
});

/** 实时校验：直接调后端，结论即数据库判断 */
const runCheck = async () => {
  if (!form.parentOneId || !form.childOneId) {
    validate.value = emptyValidate();
    return;
  }
  checking.value = true;
  try {
    validate.value = await validateHierarchyRelation({
      id: mode.value === 'edit' ? activeRelation.value?.id : undefined,
      parentOneId: form.parentOneId,
      childOneId: form.childOneId,
      relationType: form.relationType,
      payerOneId: form.payerOneId || undefined,
      changeReason: form.changeReason || undefined
    });
    if (validate.value.relationType) {
      form.relationType = validate.value.relationType;
    }
  } finally {
    checking.value = false;
  }
};

/** 展开树为平铺列表（编辑模式下作为新父节点候选，排除自身与自身后代） */
const flatten = (nodes: HierarchyNodeVO[], out: HierarchyNodeVO[] = []): HierarchyNodeVO[] => {
  nodes.forEach(node => {
    out.push(node);
    flatten(node.children ?? [], out);
  });
  return out;
};

onMounted(async () => {
  const oneId = nodeKey.value;
  if (oneId) {
    const node = await getHierarchyNode(oneId);
    currentNode.value = node ?? null;
  }

  if (mode.value === 'edit') {
    form.childOneId = currentNode.value?.oneId ?? oneId;
    const relation = await getNodeActiveRelation(form.childOneId);
    activeRelation.value = relation ?? null;
    if (relation) {
      form.parentOneId = relation.parentOneId;
      form.payerOneId = relation.payerOneId ?? '';
      form.relationType = relation.relationType || 'A2_A1';
      form.changeReason = relation.changeReason ?? '';
      history.value = await getHierarchyRelationHistory({ oneId: relation.childOneId });
    }
    // 候选父节点：排除自身及其全部后代（挂上去必然成环）
    const tree = await getHierarchy();
    const all = flatten(tree);
    const excluded = new Set<string>([form.childOneId]);
    all.forEach(item => {
      if ((item.ancestorIds ?? []).includes(form.childOneId)) excluded.add(item.oneId);
    });
    parentCandidates.value = all.filter(item => !excluded.has(item.oneId) && item.oneId);
  } else {
    // request / manage / child：预填当前选中节点（页头进入时为空 → 用户下拉自选）
    form.parentOneId = currentNode.value?.oneId ?? oneId ?? '';
    // 候选父节点：只有 A3 / A2 能做父级（request/manage 自选时需要；child 只读预填不受影响）
    const tree = await getHierarchy();
    parentCandidates.value = flatten(tree).filter(
      item => item.oneId && (item.level === 'A3' || item.level === 'A2')
    );
    unassigned.value = await getUnassignedNodes();
  }
  await runCheck();
});

// 父子节点 / Payer 变化时自动重新校验（与提交时口径一致）；层级类型随子节点级别自动推导
watch(
  () => [form.parentOneId, form.childOneId, form.payerOneId],
  () => {
    form.hierarchyType = derivedHierarchyType.value?.code ?? '';
    void runCheck();
  }
);

const submit = async (): Promise<string> => {
  await formRef.value?.validate();
  await runCheck();
  if (!validate.value.checks.length) {
    throw new Error('尚未完成校验，请稍候重试');
  }
  if (!validate.value.passed) {
    throw new Error(validate.value.blockedReason || '校验未通过，请修正关系后再提交');
  }

  if (mode.value === 'edit' && activeRelation.value?.id) {
    const message = await updateHierarchyRelation({
      id: activeRelation.value.id,
      childOneId: form.childOneId,
      parentOneId: form.parentOneId,
      relationType: form.relationType,
      payerOneId: form.payerOneId || undefined,
      effectiveFrom: form.effectiveFrom || undefined,
      effectiveTo: form.effectiveTo || undefined,
      changeReason: form.changeReason,
      remark: form.remark || undefined
    });
    markHierarchyChanged();
    return message;
  }

  if (mode.value === 'request') {
    const message = await addHierarchyRelation({
      // 层级类型按子节点级别推导落库（与后端挂载时 _hier_type_by_level 同口径）
      hierarchyType: derivedHierarchyType.value?.code ?? form.hierarchyType ?? 'LEGAL',
      relationType: form.relationType,
      parentId: form.parentOneId,
      childId: form.childOneId,
      payerOneId: form.payerOneId,
      effectiveDate: form.effectiveFrom,
      reason: form.changeReason
    });
    markHierarchyChanged();
    return message;
  }

  const message = await addHierarchyChild({
    parentOneId: form.parentOneId,
    childOneId: form.childOneId,
    relationType: form.relationType,
    payerOneId: form.payerOneId || undefined,
    effectiveFrom: form.effectiveFrom || undefined,
    effectiveTo: form.effectiveTo || undefined,
    changeReason: form.changeReason,
    remark: form.remark || undefined
  });
  markHierarchyChanged();
  return message;
};

defineExpose({ submit });
</script>

<style lang="scss" scoped>
.hier-add {
  .hier-check {
    margin-top: 12px;
    padding: 12px;
    border: 1px solid var(--g-divider);
    border-radius: 8px;
    background: #fafcfe;
  }

  .hier-check-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .hier-check-title {
    font-size: 13px;
    font-weight: 700;
  }

  .hier-conflict {
    padding: 4px 6px;
    background: #fff0f2;
    border: 1px solid #f3c3c6;
    border-radius: 6px;
    color: #9e3c48;
    font-size: 12px;
    line-height: 1.5;
  }

  .hier-section-title {
    margin: 16px 0 8px;
    font-size: 13px;
    font-weight: 700;
  }
}
</style>
