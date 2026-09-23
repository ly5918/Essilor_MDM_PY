<template>
  <div class="poc-dialog-body">
    <el-form ref="formRef" :model="form" label-width="130px">
      <!-- 业务上下文（设计节点①：选择业务场景、BU、来源系统与模板版本并创建任务） -->
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="业务场景" prop="scene">
            <el-select v-model="form.scene" style="width: 100%" placeholder="请选择业务场景">
              <el-option v-for="item in SCENE_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="BU" prop="buScope">
            <el-select v-model="form.buScope" style="width: 100%" placeholder="请选择 BU">
              <el-option v-for="item in BU_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="来源系统" prop="sourceSystem">
            <el-select v-model="form.sourceSystem" style="width: 100%" placeholder="请选择来源系统">
              <el-option v-for="item in SOURCE_SYSTEM_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="导入模板" prop="templateCode">
            <el-select v-model="form.templateCode" style="width: 100%" @change="onTemplateChange"
                       :placeholder="matchingTemplates.length ? '请选择导入模板' : '暂无匹配的模板'">
              <el-option v-for="item in matchingTemplates" :key="item.templateCode" :label="templateLabel(item)" :value="item.templateCode" />
              <template #empty>
                <div class="tpl-empty">
                  {{ templateLoadFailed
                    ? '模板加载失败：请关闭弹窗后重新打开重试'
                    : !publishedTemplates.length
                      ? (draftCount
                        ? `暂无已发布模板：有 ${draftCount} 个草稿模板尚未发布，请管理员先在「平台管理 › 导入模板管理」发布后再提交`
                        : '暂无已发布模板：请先在「平台管理 › 导入模板管理」新建模板、配置字段映射后发布')
                      : `暂无与当前业务上下文（${form.scene} / ${form.buScope || '未选BU'} / ${form.sourceSystem || '未选来源'}）匹配的已发布模板：请调整业务上下文，或让管理员发布对应上下文的模板` }}
                </div>
              </template>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <div v-if="currentTemplate" class="tpl-hint">
        模板版本：{{ currentTemplate.version }} · 字段数 {{ currentTemplate.fieldCount }} ·
        业务上下文：{{ templateContext(currentTemplate) }}
        <span class="tpl-only-published">仅显示与业务上下文匹配的已发布模板</span>
      </div>

      <!-- 模板表头要求（设计节点②「上传 Excel / CSV」：提交前确认文件与模板匹配） -->
      <div v-if="mappings.length" class="tpl-columns">
        <span class="tpl-columns-label">模板表头（{{ mappings.length }} 列，标 * 为必填）：</span>
        <span v-for="m in mappings" :key="m.sourceColumn" class="col-chip">
          {{ m.sourceColumn }}<i v-if="m.errorStrategy === 'Reject Row'">*</i>
        </span>
      </div>

      <el-form-item label="上传Excel / CSV" prop="file">
        <el-upload
          drag
          action="#"
          :auto-upload="false"
          :on-change="onFileChange"
          :on-remove="onFileRemove"
          :limit="1"
          accept=".xlsx,.xls,.csv"
          class="upload-zone"
        >
          <el-icon class="upload-ico"><UploadFilled /></el-icon>
          <div class="upload-text">点击或拖拽文件到此处上传</div>
          <div class="upload-hint">请使用「下载模板」得到的表头填写，单个文件不超过 10MB</div>
        </el-upload>
      </el-form-item>
      <!-- 文件详情（设计节点②：查看文件、Sheet 与行数） -->
      <div v-if="file" class="file-info">
        已选择：<b>{{ file.name }}</b>（{{ (file.size / 1024).toFixed(1) }} KB）· 行数与表头在提交后由文件级预检校验
      </div>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="提交后先做文件级预检（表头缺列 / 无数据行则整批退回），通过后逐行执行 DQ、批次内去重与存量匹配，按 Exact / Suspected / New / Invalid 四类分流；存在 New 行时自动发起「批量导入确认」审批。"
    />
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue';
import type { FormInstance, UploadFile } from 'element-plus';
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { listImportTemplates, listTemplateMappings, uploadImportJob } from '@/api/demo/cmdPoc';
import type { ImportTemplateVO, TemplateMappingVO } from '@/api/demo/cmdPoc/types';

defineOptions({ name: 'CmdPocBatchUploadDialog' });

defineProps<{ payload?: Record<string, unknown> }>();

const SCENE_OPTIONS = ['DOOR', 'LEGAL', 'GROUP'];
const BU_OPTIONS = ['High End', 'Mainstream'];
const SOURCE_SYSTEM_OPTIONS = ['DMS+', 'Cloud', 'SAP', 'EXCEL', 'Manual'];

const formRef = ref<FormInstance>();
/** 模板全量（含草稿）：下拉只列已发布，草稿仅用于空态提示「有几个草稿待发布」 */
const templates = ref<ImportTemplateVO[]>([]);
/** 模板接口是否加载失败（用于区分「未配置模板」与「加载失败」，给出不同引导） */
const templateLoadFailed = ref(false);
const mappings = ref<TemplateMappingVO[]>([]);
const file = ref<File | null>(null);

const form = reactive({
  scene: 'DOOR',
  buScope: '',
  sourceSystem: '',
  templateCode: ''
});

/**
 * 业务侧只能选用已发布模板（总设计 §02 Configuration-first：模板是版本化配置，
 * 须 Admin 发布后才生效；§05 泳道里「模板与规则配置」是 Admin 旁路）。
 * 草稿模板的字段映射可能仍在调整，选它会造成上传文件按错列解析。
 */
const publishedTemplates = computed(() => templates.value.filter(item => item.status === 'Published'));
const draftCount = computed(() => templates.value.length - publishedTemplates.value.length);

/**
 * 模板与业务上下文对应（总设计 §15：模板按业务上下文定位）——
 * 只列出「业务场景 / BU / 来源系统」与当前表单选择一致的已发布模板，
 * 避免出现 DOOR/Mainstream 任务里可选到别的上下文模板（文件列结构错配）。
 * 模板上下文不完整的（历史遗留）不会命中任何组合，等价于被排除；
 * Admin 侧需先在「导入模板管理」补全上下文并重新发布。
 */
const matchingTemplates = computed(() => publishedTemplates.value.filter(item =>
  (!!item.context && item.context === form.scene)
  && (!form.buScope || item.bu === form.buScope)
  && (!form.sourceSystem || item.sourceSystem === form.sourceSystem)));

/** 上下文变化后当前模板不再匹配 → 清空选择，让用户在对应列表里重选 */
watch(() => [form.scene, form.buScope, form.sourceSystem], async () => {
  if (form.templateCode && !matchingTemplates.value.some(item => item.templateCode === form.templateCode)) {
    form.templateCode = '';
    mappings.value = [];
  }
});

const currentTemplate = computed(() => templates.value.find(item => item.templateCode === form.templateCode));

const templateLabel = (item: ImportTemplateVO) => `${item.name} · ${item.version}（${item.status}）`;

const templateContext = (item: ImportTemplateVO) =>
  [item.customerType, item.bu, item.productLine, item.sourceSystem].filter(Boolean).join(' · ') || item.context;

/** 模板切换：业务上下文自动回落模板定义，仍可手工调整；同时拉取表头要求明细 */
const onTemplateChange = async () => {
  const tpl = currentTemplate.value;
  if (!tpl) {
    mappings.value = [];
    return;
  }
  if (tpl.bu) form.buScope = tpl.bu;
  if (tpl.sourceSystem) form.sourceSystem = tpl.sourceSystem;
  try {
    mappings.value = await listTemplateMappings(tpl.templateCode);
  } catch {
    mappings.value = [];
  }
};

const onFileChange = (uploadFile: UploadFile) => {
  file.value = (uploadFile.raw as File) ?? null;
};

const onFileRemove = () => {
  file.value = null;
};

const submit = async (): Promise<string> => {
  await formRef.value?.validate();
  if (!form.scene) {
    throw new Error('请选择业务场景');
  }
  if (!form.buScope) {
    throw new Error('请选择 BU');
  }
  if (!form.templateCode) {
    // 区分「没选」与「没有匹配模板」：后者是配置问题（设计 §15 需 Admin 发布对应上下文的模板），不能只提示「请选择」
    throw new Error(matchingTemplates.value.length
      ? '请选择导入模板'
      : `暂无与业务上下文（${form.scene} / ${form.buScope || '未选BU'} / ${form.sourceSystem || '未选来源'}）匹配的已发布模板：请到「平台管理 › 导入模板管理」检查模板上下文并发布，再提交`);
  }
  if (!file.value) {
    throw new Error('请选择要上传的文件');
  }
  const jobCode = await uploadImportJob({
    file: file.value,
    templateCode: form.templateCode,
    // 错误/重复策略按总设计固定规则执行（不属「新建导入任务」节点的用户输入项）
    errorStrategy: 'Reject Row',
    duplicateStrategy: 'Exact自动关联，Suspect进入治理',
    scene: form.scene,
    buScope: form.buScope,
    sourceSystem: form.sourceSystem
  });
  ElMessage.success(`任务 ${jobCode} 已创建，DQ 与去重分流完成`);
  return `导入任务 ${jobCode} 已创建：文件预检通过，行级 DQ 与四类分流完成，New 行已提交批量导入确认审批`;
};

onMounted(async () => {
  // try/catch：模板接口异常时不能让弹窗挂载中断（此前无捕获，下拉会静默为空且无任何引导）
  try {
    templates.value = await listImportTemplates();
    templateLoadFailed.value = false;
  } catch {
    templates.value = [];
    templateLoadFailed.value = true;
  }
  // 默认选中第一个与业务上下文匹配的已发布模板；选中后 onTemplateChange 会把 BU/来源系统回落为模板定义
  const matched = matchingTemplates.value[0];
  if (matched) {
    form.templateCode = matched.templateCode;
    onTemplateChange();
  }
});

defineExpose({ submit });
</script>

<style lang="scss" scoped>
.upload-zone {
  width: 100%;

  :deep(.el-upload-dragger) {
    padding: 20px;
  }
}

.upload-ico {
  font-size: 28px;
  color: var(--g-text2);
}

.upload-text {
  font-size: 13px;
  color: var(--g-text);
  margin-top: 6px;
}

.upload-hint {
  font-size: 12px;
  color: var(--g-text2);
  margin-top: 4px;
}

.tpl-hint {
  margin: 0 0 8px 130px;
  font-size: 12px;
  color: var(--g-text2);
}

/* 「仅可选已发布模板」小标：说明草稿不出现在此下拉的原因 */
.tpl-only-published {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 8px;
  font-size: 11px;
  color: var(--g-brand, #0a58ca);
  background: color-mix(in srgb, var(--g-brand, #0a58ca) 10%, transparent);
}

/* 模板下拉空态引导（未配置模板 / 加载失败两种文案） */
.tpl-empty {
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--g-text2);
  white-space: normal;
}

/* 模板表头要求（必填列标 *） */
.tpl-columns {
  margin: 0 0 14px 130px;
  font-size: 12px;
  color: var(--g-text2);
  line-height: 2;
}

.tpl-columns-label {
  margin-right: 6px;
}

.col-chip {
  display: inline-block;
  margin: 0 6px 6px 0;
  padding: 1px 8px;
  border-radius: 10px;
  background: #eef4f9;
  border: 1px solid #d3e2ee;
  color: #2c4b63;
  font-family: Consolas, Monaco, monospace;

  i {
    color: #b4392f;
    font-style: normal;
    margin-left: 2px;
  }
}

/* 文件详情 */
.file-info {
  margin: -6px 0 12px 130px;
  font-size: 12px;
  color: var(--g-text2);

  b {
    color: var(--g-text);
  }
}
</style>
