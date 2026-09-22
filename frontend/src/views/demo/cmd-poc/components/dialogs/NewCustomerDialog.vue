<template>
  <div class="poc-dialog-body">
    <!-- 动态元数据提示条 -->
    <div class="meta-banner">
      <b>动态元数据表单</b>
      <span>根据 {{ contextText }} 加载字段（{{ dynamicFields.length }} 个，其中必填 {{ requiredCount }} 个）</span>
      <el-tag type="success" size="small" effect="plain">模型版本 {{ currentVersion }}</el-tag>
      <el-button link type="primary" @click="onReload">刷新字段</el-button>
    </div>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="190px" class="nc-form">
      <div class="form-section">业务上下文</div>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="Customer Type" prop="customerType">
            <el-select v-model="form.customerType" style="width: 100%">
              <el-option v-for="item in CUSTOMER_TYPE_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="BU" prop="bu">
            <el-select v-model="form.bu" style="width: 100%">
              <el-option v-for="item in BU_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Product Line" prop="productLine">
            <el-select v-model="form.productLine" style="width: 100%">
              <el-option v-for="item in PRODUCT_LINE_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Source System" prop="sourceSystem">
            <el-select v-model="form.sourceSystem" style="width: 100%">
              <el-option v-for="item in SOURCE_SYSTEM_OPTIONS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <div class="form-section">动态客户字段</div>
      <el-row :gutter="12">
        <el-col v-for="field in dynamicFields" :key="field.code" :span="12">
          <el-form-item :prop="`dynamicValues.${field.code}`" :required="field.required">
            <template #label>
              <span class="field-label">
                {{ field.label }}
                <el-tag v-if="ocrFieldCodes.includes(field.code)" size="small" type="success" effect="plain">OCR回填</el-tag>
              </span>
            </template>
            <el-select
              v-if="field.type === 'Enum'"
              v-model="form.dynamicValues[field.code]"
              :placeholder="field.required ? '请选择' : '可选'"
              style="width: 100%"
            >
              <el-option v-for="option in enumOptions(field.code)" :key="option" :label="option" :value="option" />
            </el-select>
            <el-input v-else v-model="form.dynamicValues[field.code]" :placeholder="`请输入${field.label}`" />
          </el-form-item>
        </el-col>
        <el-col v-if="!dynamicFields.length" :span="24">
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            title="未加载到已发布字段：请在「元数据管理」发布字段后点击「刷新字段」"
          />
        </el-col>
      </el-row>

      <el-form-item label="营业执照">
        <el-button plain icon="Upload" @click="openOcr">上传并OCR识别</el-button>
        <span class="form-tip">识别结果按字段名称回填到上方「动态客户字段」，并标记 OCR回填 标签</span>
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="字段来自元数据配置，而不是写死在页面。发布新字段后刷新业务上下文即可加载。"
    />
    <el-alert
      class="submit-alert"
      type="success"
      :closable="false"
      show-icon
      title="提交申请：写入客户主档（status=pending）→ 生成统一待办 → 启动「客户创建」流程实例，进入 BU Scope 初审。"
    />

    <!--
      查重回执：提交成功后原地展开，把系统判定的匹配结论回流给提交人。
      此前回执只有一句 ElMessage toast（3 秒即消失），后端算出的 EXACT/SUSPECTED 与候选 One ID
      在 CmdCustomerSubmitVo 里一个字段都没带，业务用户提交完就彻底盲了——
      同一家公司被重复提交两次、一条在 BU 手里一条在 GC 手里互相看不见，就是这么发生的。
      仅在 Duplicate Check 命中时展开（keepOpenAfterSubmit），让提交人必须看到。
    -->
    <div v-if="submitResult" class="rcpt" :class="receiptTone">
      <div class="rcpt-head">
        <span class="rcpt-badge">查重回执</span>
        <b>{{ receiptTitle }}</b>
        <p>{{ submitResult.duplicateHint }}</p>
      </div>

      <div class="rcpt-grid">
        <div class="rcpt-cell">
          <label>本次申请 One ID</label>
          <span class="rcpt-mono">{{ submitResult.oneId || '—' }}</span>
        </div>
        <div class="rcpt-cell">
          <label>申请编号</label>
          <span class="rcpt-mono">{{ submitResult.taskNo || '—' }}</span>
        </div>
        <div class="rcpt-cell">
          <label>当前节点</label>
          <span>{{ submitResult.currentNodeName || '—' }}</span>
        </div>
        <div class="rcpt-cell">
          <label>匹配结论</label>
          <el-tag size="small" :type="matchTagType" effect="plain">{{ submitResult.matchStateName || '新客户' }}</el-tag>
        </div>
      </div>

      <div v-if="submitResult.matchedOneId" class="rcpt-peer">
        <div class="rcpt-peer-title">命中的既有记录（系统比对结果）</div>
        <table class="rcpt-table">
          <tbody>
            <tr>
              <th>One ID</th>
              <td class="rcpt-mono">{{ submitResult.matchedOneId }}</td>
            </tr>
            <tr>
              <th>客户名称</th>
              <td>{{ submitResult.matchedName || '—' }}</td>
            </tr>
            <tr>
              <th>统一社会信用代码</th>
              <td class="rcpt-mono">{{ submitResult.matchedCreditCode || '—' }}</td>
            </tr>
            <tr>
              <th>归属 BU</th>
              <td>{{ submitResult.matchedBuScope || '—' }}</td>
            </tr>
            <tr>
              <th>记录性质</th>
              <td>
                <el-tag v-if="submitResult.matchedInFlight" size="small" type="danger" effect="plain">
                  在途申请（尚未审批完成，未发布成主档）
                </el-tag>
                <el-tag v-else size="small" type="success" effect="plain">已发布主档</el-tag>
              </td>
            </tr>
            <tr v-if="submitResult.matchedTaskNo">
              <th>对方申请编号</th>
              <td class="rcpt-mono">{{ submitResult.matchedTaskNo }}</td>
            </tr>
            <tr v-if="submitResult.matchedNodeName">
              <th>对方当前节点</th>
              <td>{{ submitResult.matchedNodeName }}</td>
            </tr>
            <tr v-if="submitResult.matchedSubmitTime">
              <th>对方提交时间</th>
              <td class="rcpt-mono">{{ fmtReceiptTime(submitResult.matchedSubmitTime) }}</td>
            </tr>
            <tr>
              <th>同主体在途申请</th>
              <td>共 {{ submitResult.inFlightCount ?? 0 }} 条（含本次提交的这条）</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rcpt-foot">
        <b>下一步怎么做：</b>
        <template v-if="submitResult.matchedInFlight">
          本条申请已进入「<b>{{ submitResult.currentNodeName || 'BU Scope 初审' }}</b>」队列，与命中的在途申请
          <b>{{ submitResult.matchedTaskNo || submitResult.matchedOneId }}</b> 并行。请到左侧菜单「<b>治理与审批</b>」跟踪两条待办，
          由 Data Steward 判定是否合并到同一 One ID——<b>不要重复提交第三次</b>。
        </template>
        <template v-else>
          本条申请已进入「<b>{{ submitResult.currentNodeName || 'BU Scope 初审' }}</b>」队列，批准后将按合并流程把本条关联到
          <b>{{ submitResult.matchedOneId }}</b>，One ID 保持稳定、不做物理删除。
        </template>
      </div>
    </div>

    <!-- 嵌套 OCR 弹窗：与全局 OCR 弹窗同一组件，确认后立即回填。
         宽度与全局 OCR 弹窗保持一致（min(1040px, 94vw)）：原来 640px 时右侧
         执照原件信息的值列只剩 ~110px，名称/类型/住所被折行成碎片。 -->
    <el-dialog v-model="ocrVisible" class="poc-dialog" title="OCR识别结果" width="min(1040px, 94vw)" append-to-body destroy-on-close>
      <OcrDialog ref="ocrDialogRef" embedded @apply="onApplyOcr" />
      <template #footer>
        <el-button @click="ocrVisible = false">关闭</el-button>
        <el-button type="primary" @click="onOcrConfirm">写回表单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { submitCustomer, listModelVersions } from '@/api/demo/cmdPoc';
import type { CustomerForm, CustomerSubmitVO, OcrResultVO } from '@/api/demo/cmdPoc/types';
import { useCmdPoc } from '../../composables/useCmdPoc';
import {
  BU_OPTIONS,
  CUSTOMER_TYPE_OPTIONS,
  FIELD_ENUM_OPTIONS,
  PRODUCT_LINE_OPTIONS,
  SOURCE_SYSTEM_OPTIONS
} from '../../constants/options';
import OcrDialog from './OcrDialog.vue';

defineOptions({ name: 'CmdPocNewCustomerDialog' });

defineProps<{ payload?: Record<string, unknown> }>();

const { publishedFields, loadCustomers, ocrPrefill, setOcrPrefill, refreshBadge } = useCmdPoc();

/** 已在「业务上下文」维护或由系统托管的字段，不在动态区重复渲染 */
const CONTEXT_FIELD_CODES = ['customer_type', 'bu_scope', 'product_line', 'source_system', 'status'];

/** 动态字段演示默认值（国家/地区默认中国，可在表单中修改） */
const FIELD_DEFAULTS: Record<string, string> = { country: '中国' };

/** OCR 结果 → 元数据字段名称 → 动态字段编码（写回目标） */
const CORE_FIELD_MAP: Record<string, keyof CustomerForm> = {
  legal_name: 'legalName',
  credit_code: 'creditCode',
  address: 'address',
  payer_id: 'payerId'
};

const formRef = ref<FormInstance>();
const ocrDialogRef = ref<InstanceType<typeof OcrDialog>>();
const ocrVisible = ref(false);
/** 本次 OCR 回填命中的字段编码（用于打「OCR回填」标签，让回填结果可见） */
const ocrFieldCodes = ref<string[]>([]);

/** 当前生效的元数据模型版本（打开弹窗时实时读取，替代早期硬编码的假版本号） */
const currentVersion = ref('…');
onMounted(async () => {
  try {
    const versions = await listModelVersions();
    currentVersion.value = versions.find(v => v.status === 'Current')?.version ?? versions[0]?.version ?? currentVersion.value;
  } catch {
    /* 版本号读取失败不打断表单，保持占位 */
  }
});

const form = reactive<CustomerForm & { dynamicValues: Record<string, string> }>({
  legalName: '',
  creditCode: '',
  address: '',
  customerType: 'Door',
  bu: 'High End',
  productLine: 'Frame',
  sourceSystem: 'Cloud',
  dynamicValues: {}
});

/** 动态必填字段的校验规则随业务上下文变化 */
const rules = computed<FormRules>(() => {
  const dynamicRules: FormRules = {};
  dynamicFields.value
    .filter(field => field.required)
    .forEach(field => {
      dynamicRules[`dynamicValues.${field.code}`] = [{ required: true, message: `请输入${field.label}`, trigger: 'blur' }];
    });
  return dynamicRules;
});

/** 按业务上下文过滤动态字段：BU / Customer Type 命中或取值为 All */
const dynamicFields = computed(() =>
  publishedFields.value.filter(
    field =>
      !CONTEXT_FIELD_CODES.includes(field.code) &&
      (field.bu === form.bu || field.bu === 'All') &&
      (field.customerType === form.customerType || field.customerType === 'All')
  )
);

const contextText = computed(() => `${form.customerType} · ${form.bu} · ${form.productLine} · ${form.sourceSystem}`);

/** 当前上下文下必填字段数（提示条展示，提交时按同一口径校验） */
const requiredCount = computed(() => dynamicFields.value.filter(field => field.required).length);

/** 枚举字段选项：值集明细未落库，POC 阶段按字段编码取前端常量 */
const enumOptions = (code: string): string[] => FIELD_ENUM_OPTIONS[code] ?? ['A', 'B', 'C'];

/** 上下文 / 字段集变化：清理不适用字段取值，并为演示字段补默认值 */
watch(
  dynamicFields,
  fields => {
    const codes = fields.map(field => field.code);
    Object.keys(form.dynamicValues).forEach(code => {
      if (!codes.includes(code) && !CONTEXT_FIELD_CODES.includes(code)) delete form.dynamicValues[code];
    });
    Object.entries(FIELD_DEFAULTS).forEach(([code, value]) => {
      if (codes.includes(code) && !form.dynamicValues[code]) form.dynamicValues[code] = value;
    });
  },
  { immediate: true }
);

/** 消费全局 OCR 弹窗暂存的结果（顶部「查看OCR识别结果」→ 写回表单 后打开本弹窗） */
onMounted(() => {
  const pending = ocrPrefill.value;
  if (pending?.length) {
    onApplyOcr(pending);
    ElMessage.success(`已回填上次 OCR 识别结果（${pending.length} 个字段）`);
  }
});

/** 表单弹窗已打开时，监听共享通道变化并立即回填（解决「先打开表单再点全局 OCR 写回」不生效） */
watch(
  ocrPrefill,
  (pending) => {
    if (pending?.length) {
      onApplyOcr(pending);
      ElMessage.success(`已回填 OCR 识别结果（${pending.length} 个字段）`);
    }
  }
);

const onReload = () => {
  // 重新触发上下文过滤即可（字段源为共享缓存，发布后自动包含新字段）
};

const openOcr = () => {
  ocrVisible.value = true;
};

/** 嵌套 OCR 弹窗的「写回表单」 */
const onOcrConfirm = async () => {
  try {
    const message = await ocrDialogRef.value?.submit();
    ocrVisible.value = false;
    if (message) ElMessage.success(message);
  } catch (error) {
    // 未上传营业执照等前置校验失败：保持 OCR 弹窗打开，只提示不关闭
    if (error instanceof Error) ElMessage.warning(error.message);
  }
};

/**
 * OCR 结果回填：
 * 1. 按字段编码写入 dynamicValues（兜底，防止当前字段不可见时丢失值）；
 * 2. 按识别字段名称匹配可见动态字段标签，回填并打「OCR回填」标签；
 * 3. 同步核心主档列，保证提交时主档列有值。
 */
const onApplyOcr = (results: OcrResultVO[]) => {
  const filledLabels: string[] = [];
  results.forEach(item => {
    if (item.code) form.dynamicValues[item.code] = item.value;
    const coreKey = CORE_FIELD_MAP[item.code];
    if (coreKey) {
      (form as unknown as Record<string, string>)[coreKey] = item.value;
    }
    const target = dynamicFields.value.find(field => field.label === item.field);
    if (target) {
      form.dynamicValues[target.code] = item.value;
      filledLabels.push(target.label);
    }
  });
  ocrFieldCodes.value = dynamicFields.value
    .filter(field => results.some(result => result.field === field.label))
    .map(field => field.code);
  if (!filledLabels.length) {
    ElMessage.warning('识别字段未匹配到已发布元数据字段，请检查字段名称');
  }
  // 已消费，避免下次打开表单重复回填
  setOcrPrefill(null);
};

/**
 * 查重回执：仅当 Duplicate Check 命中重复（EXACT / SUSPECTED）时填充并在原地展开。
 * 未命中时保持 null，仍走原来的一行 toast + 关窗，不打扰正常提交。
 */
const submitResult = ref<CustomerSubmitVO | null>(null);

/** 命中重复时保持弹窗打开（DialogHost 的 keepOpenAfterSubmit 机制），让提交人必须在原地看到结论 */
const keepOpenAfterSubmit = computed(() => submitResult.value !== null);

/**
 * 回执展开后主按钮语义从「提交申请」改为「完成并关闭」。
 * 不改的话用户会以为还要再点一次，手一抖就把同一家客户第三次提交进库。
 */
const confirmText = computed(() => (submitResult.value ? '完成并关闭' : undefined));

/** 回执配色：命中在途申请（对方还没审完）比命中已发布主档更需要注意 */
const receiptTone = computed(() => (submitResult.value?.matchedInFlight ? 'is-danger' : 'is-warn'));

const receiptTitle = computed(() => {
  const r = submitResult.value;
  if (!r) return '';
  return r.matchedInFlight
    ? '该客户已有一条「在途申请」尚未审批完成'
    : '该客户已存在「已发布主档」';
});

/** 精准重复（信用代码完全一致）标红，疑似重复（仅名称相近）标黄 */
const matchTagType = computed(() => (submitResult.value?.matchState === 'EXACT' ? 'danger' : 'warning'));

/** 回执时间展示：到分钟（后端返回 ISO 字符串） */
const fmtReceiptTime = (value?: string) => (value ? value.replace('T', ' ').slice(0, 16) : '');

/** 提交申请：后端落主档 + 生成待办 + 启动流程实例，随后刷新客户列表 */
const submit = async (): Promise<string> => {
  // 已出回执时主按钮表示「完成并关闭」：直接返回，绝不二次提交
  // （否则同一家客户会被反复建号，正是本功能要拦的场景）
  if (submitResult.value) {
    return `本次提交已完成：One ID ${submitResult.value.oneId ?? '-'}｜申请编号 ${submitResult.value.taskNo ?? '-'}`;
  }
  // 1) 前端先按「动态必填字段」校验：缺失字段以红字标注并汇总提示，
  //    不再让空值一路打到后端触发未捕获异常（测试报告 BUG-2）。
  try {
    await formRef.value?.validate();
  } catch {
    const missing = dynamicFields.value
      .filter(field => field.required && !String(form.dynamicValues[field.code] ?? '').trim())
      .map(field => field.label);
    throw new Error(
      missing.length
        ? `还有 ${missing.length} 个必填字段未填写：${missing.join('、')}（表单中已红字标注）`
        : '表单校验未通过，请检查标红的字段'
    );
  }
  Object.entries(CORE_FIELD_MAP).forEach(([code, key]) => {
    const value = form.dynamicValues[code];
    if (value) (form as unknown as Record<string, string>)[key as string] = value;
  });
  const result = await submitCustomer(form);
  await loadCustomers();
  refreshBadge();
  const node = result.currentNodeName ?? 'BU Scope 初审';
  // 2) Duplicate Check 命中 → 原地展开查重回执（讲清「命中谁 / 对方是否还在途 / 下一步做什么」），
  //    而不是吞掉结论只给一句成功 toast。这是「同一家公司被重复提交两次」信息断点的根治点。
  if (result.duplicateFlag === 'Y') {
    submitResult.value = result;
    return `客户申请已提交，但系统判定为「${result.matchStateName ?? '疑似重复'}」，请查看下方《查重回执》`;
  }
  return `客户申请已提交：One ID ${result.oneId ?? '-'}｜申请编号 ${result.taskNo ?? '-'}，已进入「${node}」，可在「治理与审批」查看待办`;
};

defineExpose({ submit, keepOpenAfterSubmit, confirmText });
</script>

<style scoped lang="scss">
/**
 * 标签列防挤压
 * <p>
 * el-form-item 是 flex 容器：标签虽然有 label-width(150px)，但默认 flex-shrink:1，
 * 会被右侧输入框挤扁 —— "统一社会信用代码" 因此折成三行、相邻行的标签视觉上叠在一起。
 * 这里把标签固定为 150px 不参与压缩，并收紧多行标签的行距；
 * 字段名 + 「OCR回填」标签放不下时，标签整体右对齐换行，而不是挤出格子。
 */
.nc-form {
  :deep(.el-form-item__label) {
    flex: 0 0 auto;
    line-height: 1.5;
    padding-right: 10px;
    white-space: normal;
  }
}

.field-label {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 100%;

  /* 「OCR回填」标签用紧凑尺寸：让它能和最长的字段名（统一社会信用代码）同处一行，
     不再把标签列撑成两行 */
  :deep(.el-tag) {
    height: 18px;
    padding: 0 5px;
    font-size: 11px;
    line-height: 16px;
  }
}

.submit-alert {
  margin-top: 8px;
}

/* ===== 查重回执面板 =====
   设计意图：它替代了原来 3 秒即消失的 toast，必须一眼看到三件事——
   ① 命中了谁（One ID / 名称 / 信用代码）；② 对方是「已发布主档」还是「在途申请」；③ 下一步做什么。
   因此表头用「严重度色带 + 徽标」，明细用两列表格，避免整块彩色 alert 造成的信息扁平化。 */
.rcpt {
  margin-top: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  background: var(--el-bg-color);

  &.is-danger {
    border-color: var(--el-color-danger-light-5);

    .rcpt-head {
      background: var(--el-color-danger-light-9);
      border-bottom-color: var(--el-color-danger-light-7);
    }

    .rcpt-badge {
      background: var(--el-color-danger);
      color: #fff;
    }

    .rcpt-peer-title {
      color: var(--el-color-danger);
    }
  }

  &.is-warn {
    border-color: var(--el-color-warning-light-5);

    .rcpt-head {
      background: var(--el-color-warning-light-9);
      border-bottom-color: var(--el-color-warning-light-7);
    }

    .rcpt-badge {
      background: var(--el-color-warning);
      color: #fff;
    }

    .rcpt-peer-title {
      color: var(--el-color-warning);
    }
  }
}

.rcpt-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  b {
    font-size: 13.5px;
    color: var(--g-text);
  }

  p {
    flex: 1 1 100%;
    margin: 2px 0 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: var(--g-text2);
  }
}

.rcpt-badge {
  flex: 0 0 auto;
  padding: 1px 7px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

/* 顶部四格摘要：One ID / 申请编号 / 当前节点 / 匹配结论 */
.rcpt-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0 16px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.rcpt-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;

  label {
    font-size: 11.5px;
    color: var(--g-text2);
  }

  span {
    font-size: 12.5px;
    color: var(--g-text);
    overflow-wrap: anywhere;
  }
}

/* 命中记录明细：标签列固定宽 + 值列 minmax(0,1fr)，长名称与长信用代码都不撑破弹窗 */
.rcpt-peer {
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.rcpt-peer-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
}

.rcpt-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;

  th,
  td {
    padding: 4px 8px;
    font-size: 12.5px;
    line-height: 1.5;
    text-align: left;
    vertical-align: top;
    border-bottom: 1px solid var(--el-border-color-lighter);
    overflow-wrap: anywhere;
  }

  th {
    width: 132px;
    font-weight: 500;
    color: var(--g-text2);
  }

  td {
    color: var(--g-text);
  }

  tr:last-child th,
  tr:last-child td {
    border-bottom: none;
  }
}

.rcpt-mono {
  font-family: var(--g-font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
}

.rcpt-foot {
  padding: 10px 14px;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--g-text2);
  background: var(--el-fill-color-lighter);

  b {
    color: var(--g-text);
  }
}

/* 窄屏（≤1100px）回执摘要由四列折成两列，避免每个格子只剩 60px 导致 One ID 折行 */
@media (max-width: 1100px) {
  .rcpt-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 16px;
  }
}
</style>
