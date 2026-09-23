<template>
  <div class="poc-dialog-body">
    <!-- 平台管理 › 导入Template（总设计 V6.1 第 15 页：模板版本 / 来源列 / 目标字段 / 转换与错误策略）。
         这里是「导入模板」的治理入口——与「字段与值集（元数据字段）」不是同一件事：
         模板 = 某个业务上下文下的一份上传文件契约（表头 → 目标字段映射 + 必填/错误策略）。
         管线全链路由 cmd_import_template_mapping 驱动：这里新增/编辑字段后，
         模板下载表头、上传表头预检、行级 DQ（必填）、行明细 JSON 自动跟上，无需改代码。 -->
    <div class="tpl-toolbar">
      <el-select
        v-model="currentCode"
        style="width: 340px"
        placeholder="暂无模板，请先新建"
        @change="onTemplateChange"
      >
        <el-option
          v-for="item in templates"
          :key="item.templateCode"
          :value="item.templateCode"
          :label="`${item.name} · ${item.version}（${item.status}）`"
        />
      </el-select>
      <el-tag
        v-if="currentTemplate"
        :type="currentTemplate.status === 'Published' ? 'success' : 'warning'"
        size="small"
      >
        {{ currentTemplate.status }}
      </el-tag>
      <span class="tpl-toolbar-spacer" />
      <el-button
        plain
        size="small"
        icon="Download"
        :disabled="!currentCode"
        :loading="downloading === currentCode"
        @click="onDownload"
      >
        下载模板
      </el-button>
      <template v-if="isAdmin">
        <el-button plain size="small" icon="Edit" :disabled="!currentTemplate" @click="onEditTemplate">
          编辑模板
        </el-button>
        <el-button
          v-if="currentTemplate && currentTemplate.status === 'Draft'"
          type="success"
          plain
          size="small"
          :loading="statusSaving"
          @click="onToggleStatus('Published')"
        >
          发布
        </el-button>
        <el-button
          v-else-if="currentTemplate"
          plain
          size="small"
          :loading="statusSaving"
          @click="onToggleStatus('Draft')"
        >
          停用
        </el-button>
        <el-button type="primary" size="small" icon="Plus" @click="onAddTemplate">新建模板</el-button>
      </template>
    </div>

    <!-- 业务上下文摘要：说明这份模板"在什么业务场景下被选用"，与「字段与值集管理」区分开 -->
    <div v-if="currentTemplate" class="tpl-context">
      <span class="tpl-context-title">业务上下文</span>
      <el-tag
        v-for="tag in contextTags"
        :key="tag"
        class="tpl-context-tag"
        size="small"
        effect="plain"
        type="info"
      >
        {{ tag }}
      </el-tag>
      <span class="tpl-context-code">模板编码 {{ currentTemplate.templateCode }}</span>
    </div>

    <el-alert
      v-if="!loading && !templates.length"
      class="m-b-12"
      type="warning"
      :closable="false"
      show-icon
      title="暂无导入模板"
      description="点击右上「新建模板」按业务上下文（场景 / BU / 客户类型 / 产品线 / 来源系统）创建模板，配置字段映射后点「发布」即可在「批量导入 › 新建导入任务」中选用。"
    />

    <div class="tpl-section-title">
      模板字段映射（上传文件表头 → 目标字段）
      <span class="tpl-count">{{ mappings.length }} 个字段</span>
      <span class="tpl-toolbar-spacer" />
      <el-button
        v-if="isAdmin && currentCode && missingCoreFields.length"
        type="warning"
        plain
        size="small"
        icon="MagicStick"
        :loading="coreFilling"
        @click="onFillCore"
      >
        一键补齐主键字段
      </el-button>
      <el-button
        v-if="isAdmin"
        type="primary"
        size="small"
        icon="Plus"
        :disabled="!currentCode"
        @click="onAdd"
      >
        新增上传字段
      </el-button>
    </div>

    <el-alert
      v-if="isAdmin && currentCode && missingCoreFields.length"
      class="m-b-12"
      type="warning"
      :closable="false"
      show-icon
      :title="`缺少主键字段：${missingCoreFields.join('、')}`"
      :description="`主键字段是上传预检、存量查重与发布建主档的锚点，也是模板发布的前置条件（受保护、不可删除）。点右侧「一键补齐主键字段」自动补上，字段编码无需手输。`"
    />

    <el-table v-loading="loading" border :data="mappings" class="data-table" max-height="340">
      <el-table-column label="源列" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="tpl-source">{{ row.sourceColumn }}</span>
          <el-tag v-if="isCore(row)" class="tpl-core-tag" size="small" type="danger" effect="plain">主键</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标字段" prop="targetField" min-width="130" show-overflow-tooltip />
      <el-table-column label="字段名称" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">{{ row.fieldName || '—' }}</template>
      </el-table-column>
      <el-table-column label="类型" width="80" align="center">
        <template #default="{ row }">{{ row.dataType || 'Text' }}</template>
      </el-table-column>
      <el-table-column label="必填" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.isRequired === 'Y' ? 'danger' : 'info'" size="small">
            {{ row.isRequired === 'Y' ? '必填' : '选填' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="错误策略" width="110" align="center">
        <template #default="{ row }">
          <span class="tpl-strategy">{{ row.errorStrategy || (row.isRequired === 'Y' ? 'Reject Row' : 'Warning Row') }}</span>
        </template>
      </el-table-column>
      <el-table-column label="转换规则" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.transform || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="操作" width="130" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="onEdit(row)">编辑</el-button>
          <el-button
            link
            :type="isCore(row) ? 'info' : 'danger'"
            size="small"
            :disabled="isCore(row)"
            :title="isCore(row) ? '主键字段（去重 / 存量匹配锚点）不允许删除' : '从模板中移除该列'"
            @click="onDelete(row)"
          >删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-hint">{{ currentCode ? '暂无字段映射：请点右上「新增上传字段」' : '请先新建模板' }}</span>
      </template>
    </el-table>

    <el-alert
      class="m-t-12"
      type="info"
      :closable="false"
      show-icon
      title="可配置化：新增字段即时生效——模板下载自动带新列；上传预检强制全部必填列（选填列缺失按默认值 / 空值放行，存量文件可继续导入）；必填列缺失走行级 DQ（Reject Row）；整行数据落 cmd_import_row（raw/parsed JSON）。客户名称与统一社会信用代码是去重 / 存量匹配的主键字段，受保护不可删除，也是模板发布的前置条件（新建模板已自动带上，历史模板可用「一键补齐主键字段」）。"
    />

    <!-- 新增 / 编辑字段表单（内层弹窗） -->
    <el-dialog
      v-model="formVisible"
      :title="form.id ? `编辑字段：${form.columnName}` : '新增上传字段'"
      width="520px"
      append-to-body
    >
      <el-form :model="form" label-width="96px">
        <el-form-item label="源列名" required>
          <el-input v-model="form.columnName" placeholder="上传文件的表头名，如：客户邮箱" maxlength="60" />
        </el-form-item>
        <el-form-item label="字段编码" :required="!form.id">
          <el-input v-model="form.fieldCode" :disabled="!!form.id" placeholder="如 customer_email（小写下划线）" maxlength="60" />
        </el-form-item>
        <el-form-item label="字段名称">
          <el-input v-model="form.fieldName" placeholder="如：客户邮箱" maxlength="60" />
        </el-form-item>
        <el-form-item label="数据类型">
          <el-select v-model="form.dataType" style="width: 100%">
            <el-option label="Text 文本" value="Text" />
            <el-option label="Number 数值" value="Number" />
            <el-option label="Date 日期" value="Date" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否必填">
          <el-switch v-model="form.requiredBool" :disabled="isCoreForm" />
          <span v-if="isCoreForm" class="tpl-core-hint">主键字段必须保持必填</span>
        </el-form-item>
        <el-form-item label="默认值">
          <el-input v-model="form.defaultValue" placeholder="上传缺失该列时的兜底值（可空）" maxlength="120" />
        </el-form-item>
        <el-form-item label="转换规则">
          <el-input v-model="form.convertRule" placeholder="如 Trim / Upper / DateFormat(yyyy-MM-dd)（可空）" maxlength="120" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建 / 编辑模板业务上下文（内层弹窗） -->
    <el-dialog
      v-model="tplFormVisible"
      :title="tplForm.id ? `编辑模板：${tplForm.templateName}` : '新建导入模板'"
      width="560px"
      append-to-body
    >
      <el-form :model="tplForm" label-width="96px">
        <el-form-item label="模板名称" required>
          <el-input v-model="tplForm.templateName" placeholder="如：Door_HighEnd_Frame" maxlength="60" />
        </el-form-item>
        <el-form-item label="模板编码">
          <el-input
            v-model="tplForm.templateCode"
            :disabled="!!tplForm.id"
            placeholder="留空按业务上下文自动生成，如 TPL_DOOR_HIGHEND_FRAME"
            maxlength="60"
          />
        </el-form-item>
        <el-form-item label="业务场景" required>
          <el-select v-model="tplForm.scene" style="width: 100%">
            <el-option v-for="s in SCENES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="归属 BU">
          <el-select v-model="tplForm.buScope" clearable placeholder="High End / Mainstream" style="width: 100%">
            <el-option v-for="b in BUS" :key="b" :label="b" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="tplForm.customerType" clearable placeholder="Door / Payer / A1 / A2 / A3" style="width: 100%">
            <el-option v-for="c in CUSTOMER_TYPES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="产品线">
          <el-select v-model="tplForm.productLine" clearable placeholder="Lens / Frame" style="width: 100%">
            <el-option v-for="p in PRODUCT_LINES" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源系统">
          <el-select v-model="tplForm.sourceSystem" clearable placeholder="DMS+ / Cloud" style="width: 100%">
            <el-option v-for="s in SOURCE_SYSTEMS" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板版本">
          <el-input v-model="tplForm.versionNo" placeholder="v1" maxlength="20" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="tplForm.remark" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tplFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="tplSaving" @click="onSaveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  deleteTemplateMapping,
  downloadImportTemplate,
  fillCoreTemplateMappings,
  listImportTemplates,
  listTemplateMappings,
  saveImportTemplate,
  saveTemplateMapping,
  setImportTemplateStatus
} from '@/api/demo/cmdPoc';
import type {
  ImportTemplateSaveForm,
  ImportTemplateVO,
  TemplateMappingSaveForm,
  TemplateMappingVO
} from '@/api/demo/cmdPoc/types';
import { useCmdPoc } from '../../composables/useCmdPoc';

defineOptions({ name: 'CmdPocTemplateDialog' });

defineProps<{ payload?: Record<string, unknown> }>();

const { roleKey } = useCmdPoc();
/**
 * 管理能力仅 Platform Admin（总设计第 15 页：导入模板是平台管理页）。
 * 其他角色（批量导入页的「下载模板」入口）打开同一弹窗时为只读视图：
 * 仍能看到业务上下文 / 字段映射与下载——因为下载表头由同一份 mapping 动态生成，
 * Admin 在这里建模板 / 增删字段后，所有角色下载到的模板即时同步。
 */
const isAdmin = computed(() => roleKey.value === 'admin');

// 业务上下文字典：与「下载模板」「新建导入任务」弹窗的下拉同口径
const SCENES = ['DOOR', 'PAYER'];
const BUS = ['High End', 'Mainstream'];
const CUSTOMER_TYPES = ['Door', 'Payer', 'A1', 'A2', 'A3'];
const PRODUCT_LINES = ['Lens', 'Frame'];
const SOURCE_SYSTEMS = ['DMS+', 'Cloud'];

const loading = ref(false);
const saving = ref(false);
const downloading = ref('');
const statusSaving = ref(false);
const coreFilling = ref(false);
const templates = ref<ImportTemplateVO[]>([]);
const mappings = ref<TemplateMappingVO[]>([]);
const currentCode = ref('');

/** 管线主键字段：去重 / 存量匹配 / 发布建主档的锚点，前端与后端双重保护 */
const CORE_FIELDS = ['legal_name', 'credit_code'];

const currentTemplate = computed(() => templates.value.find(item => item.templateCode === currentCode.value));

/** 业务上下文标签：让「这份模板服务于哪个业务场景」一目了然 */
const contextTags = computed(() => {
  const t = currentTemplate.value;
  if (!t) return [] as string[];
  return [
    t.context && `场景 ${t.context}`,
    t.bu && `BU ${t.bu}`,
    t.customerType && `客户类型 ${t.customerType}`,
    t.productLine && `产品线 ${t.productLine}`,
    t.sourceSystem && `来源系统 ${t.sourceSystem}`,
    t.version && `版本 ${t.version}`
  ].filter(Boolean) as string[];
});

const isCore = (row: TemplateMappingVO | Record<string, unknown>) =>
  CORE_FIELDS.includes((row as TemplateMappingVO).targetField);

/** 主键字段中文名：用于「缺少主键字段」提示与一键补齐 */
const CORE_FIELD_LABELS: Record<string, string> = {
  legal_name: '客户法定名称',
  credit_code: '统一社会信用代码'
};

/** 当前模板缺失的主键字段（发布校验会拒绝，UI 提前提示 + 一键补齐） */
const missingCoreFields = computed(() =>
  CORE_FIELDS.filter(f => !mappings.value.some(m => m.targetField === f)).map(f => CORE_FIELD_LABELS[f])
);

const defaultForm = (): TemplateMappingSaveForm & { requiredBool: boolean } => ({
  id: undefined,
  templateCode: '',
  columnName: '',
  fieldCode: '',
  fieldName: '',
  dataType: 'Text',
  isRequired: 'N',
  defaultValue: '',
  convertRule: '',
  remark: '',
  requiredBool: false
});
const form = ref(defaultForm());
const formVisible = ref(false);
const isCoreForm = computed(() => !!form.value.id && CORE_FIELDS.includes(form.value.fieldCode ?? ''));

/* ---- 模板业务上下文表单 ---- */
const defaultTplForm = (): ImportTemplateSaveForm => ({
  id: undefined,
  templateCode: '',
  templateName: '',
  scene: SCENES[0],
  buScope: '',
  customerType: '',
  productLine: '',
  sourceSystem: '',
  versionNo: 'v1',
  remark: ''
});
const tplForm = ref(defaultTplForm());
const tplFormVisible = ref(false);
const tplSaving = ref(false);

const loadMappings = async () => {
  if (!currentCode.value) {
    mappings.value = [];
    return;
  }
  loading.value = true;
  try {
    mappings.value = await listTemplateMappings(currentCode.value);
  } finally {
    loading.value = false;
  }
};

/** 拉模板清单并保证 currentCode 有效（失效时回落首个已发布 / 首个模板） */
const loadTemplates = async () => {
  templates.value = await listImportTemplates();
  const exists = templates.value.some(item => item.templateCode === currentCode.value);
  if (!exists) {
    const preferred = templates.value.find(item => item.status === 'Published') ?? templates.value[0];
    currentCode.value = preferred ? preferred.templateCode : '';
  }
  await loadMappings();
};

const onTemplateChange = () => loadMappings();

/** 下载模板：后端按当前字段映射动态生成仅含表头的 Excel（新增列自动包含） */
const onDownload = async () => {
  const item = currentTemplate.value;
  if (!item) return;
  downloading.value = item.templateCode;
  try {
    await downloadImportTemplate(item.templateCode, `${item.name}_${item.version}.xlsx`);
    ElMessage.success(`模板已下载：${item.name}_${item.version}.xlsx`);
  } finally {
    downloading.value = '';
  }
};

/* ---- 模板：新建 / 编辑 / 发布 ---- */
const onAddTemplate = () => {
  tplForm.value = { ...defaultTplForm(), scene: currentTemplate.value?.context || SCENES[0] };
  tplFormVisible.value = true;
};

const onEditTemplate = () => {
  const t = currentTemplate.value;
  if (!t) return;
  tplForm.value = {
    id: undefined,
    templateCode: t.templateCode,
    templateName: t.name,
    scene: t.context || SCENES[0],
    buScope: t.bu ?? '',
    customerType: t.customerType ?? '',
    productLine: t.productLine ?? '',
    sourceSystem: t.sourceSystem ?? '',
    versionNo: t.version || 'v1',
    remark: ''
  };
  // 编辑走 id 分支（后端按 id 更新业务上下文）；id 从模板列表行取
  tplForm.value.id = t.id;
  tplFormVisible.value = true;
};

const onSaveTemplate = async () => {
  if (!tplForm.value.templateName.trim()) {
    ElMessage.warning('模板名称不能为空');
    return;
  }
  const isCreate = !tplForm.value.id;
  const createdName = tplForm.value.templateName;
  tplSaving.value = true;
  try {
    const msg = await saveImportTemplate(tplForm.value);
    ElMessage.success(msg);
    tplFormVisible.value = false;
    if (isCreate) {
      // 新建后自动切到新模板（编码可能由后端按业务上下文生成，按名称回找）
      templates.value = await listImportTemplates();
      const created = templates.value.find(item => item.name === createdName);
      if (created) currentCode.value = created.templateCode;
      await loadMappings();
    } else {
      await loadTemplates();
    }
  } finally {
    tplSaving.value = false;
  }
};

const onToggleStatus = async (next: 'Published' | 'Draft') => {
  const item = currentTemplate.value;
  if (!item) return;

  // 发布前置校验：缺主键字段时先引导补齐，不把用户丢在报错里
  let autoFilled = false;
  if (next === 'Published' && missingCoreFields.value.length) {
    try {
      await ElMessageBox.confirm(
        `模板「${item.name}」缺少主键字段：${missingCoreFields.value.join('、')}。` +
        '主键字段是上传预检与存量查重的锚点，发布前必须存在。是否自动补齐后继续发布？',
        '自动补齐主键字段',
        { type: 'warning', confirmButtonText: '补齐并发布', cancelButtonText: '取消' }
      );
    } catch {
      return;
    }
    await onFillCore(true);
    if (missingCoreFields.value.length) return;
    autoFilled = true;  // 已在本步确认过，不再弹第二次确认框
  }

  if (!autoFilled) {
    try {
      await ElMessageBox.confirm(
        next === 'Published'
          ? `发布模板「${item.name}」？发布后可在「批量导入 › 新建导入任务」中选用。`
          : `停用模板「${item.name}」？停用后新建导入任务将不再可选该模板，历史批次不受影响。`,
        next === 'Published' ? '发布模板' : '停用模板',
        { type: 'warning' }
      );
    } catch {
      return;
    }
  }
  statusSaving.value = true;
  try {
    const msg = await setImportTemplateStatus(item.templateCode, next);
    ElMessage.success(msg);
    await loadTemplates();
  } finally {
    statusSaving.value = false;
  }
};

/** 一键补齐主键字段（客户法定名称 / 统一社会信用代码）；silent=true 时不弹成功提示（发布流程内已提示） */
const onFillCore = async (silent = false) => {
  if (!currentCode.value) return;
  coreFilling.value = true;
  try {
    const msg = await fillCoreTemplateMappings(currentCode.value);
    if (!silent) ElMessage.success(msg);
    await loadMappings();
  } finally {
    coreFilling.value = false;
  }
};

/* ---- 模板字段映射：新增 / 编辑 / 删除 ---- */
const onAdd = () => {
  form.value = { ...defaultForm(), templateCode: currentCode.value };
  formVisible.value = true;
};

const onEdit = (row: TemplateMappingVO | Record<string, unknown>) => {
  const item = row as TemplateMappingVO;
  form.value = {
    id: item.id,
    templateCode: item.templateCode ?? currentCode.value,
    columnName: item.sourceColumn,
    fieldCode: item.targetField,
    fieldName: item.fieldName ?? '',
    dataType: item.dataType ?? 'Text',
    isRequired: item.isRequired ?? 'N',
    defaultValue: item.defaultValue ?? '',
    convertRule: item.transform ?? '',
    remark: '',
    requiredBool: item.isRequired === 'Y'
  };
  formVisible.value = true;
};

const onSave = async () => {
  if (!form.value.columnName.trim()) {
    ElMessage.warning('源列名不能为空');
    return;
  }
  if (!form.value.id && !form.value.fieldCode?.trim()) {
    ElMessage.warning('新增字段必须填写字段编码');
    return;
  }
  // 主键字段（去重 / 存量匹配锚点）必须必填，避免手工新增时漏勾
  if (CORE_FIELDS.includes((form.value.fieldCode ?? '').trim())) {
    form.value.requiredBool = true;
  }
  form.value.isRequired = form.value.requiredBool ? 'Y' : 'N';
  saving.value = true;
  try {
    const msg = await saveTemplateMapping(form.value);
    ElMessage.success(msg);
    formVisible.value = false;
    await loadMappings();
  } finally {
    saving.value = false;
  }
};

const onDelete = async (row: TemplateMappingVO | Record<string, unknown>) => {
  const item = row as TemplateMappingVO;
  if (item.id === undefined) return;
  try {
    await ElMessageBox.confirm(
      `确定从模板中移除「${item.sourceColumn}」？已上传的历史批次数据不受影响。`,
      '删除字段',
      { type: 'warning' }
    );
  } catch {
    return;
  }
  const msg = await deleteTemplateMapping(item.id);
  ElMessage.success(msg);
  await loadMappings();
};

const submit = async (): Promise<string> => {
  await loadTemplates();
  return `模板 ${templates.value.length} 个；当前模板 ${mappings.value.length} 个字段（配置即时生效）`;
};

onMounted(async () => {
  loading.value = true;
  try {
    await loadTemplates();
  } catch (error) {
    ElMessage.error(`导入模板加载失败：${(error as Error)?.message ?? '未知错误'}`);
  } finally {
    loading.value = false;
  }
});

defineExpose({ submit });
</script>

<style lang="scss" scoped>
.tpl-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;

  &-spacer {
    flex: 1;
  }
}

.tpl-context {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--el-fill-color-lighter);

  &-title {
    font-size: 12px;
    font-weight: 700;
    color: var(--g-text);
  }

  &-tag {
    font-size: 12px;
  }

  &-code {
    margin-left: auto;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
}

.tpl-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--g-text);
}

.tpl-count {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.tpl-strategy {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tpl-source {
  margin-right: 6px;
}

.tpl-core-tag {
  transform: scale(0.9);
}

.tpl-core-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-color-warning);
}

.empty-hint {
  font-size: 12px;
  color: var(--g-text2);
}
</style>
