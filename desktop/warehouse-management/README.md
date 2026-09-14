# نسخة Windows — نظام إدارة المخزن

هذه الحزمة هي عميل سطح مكتب خفيف لنظام إدارة المخزن. لا تحتوي على قاعدة
بيانات محلية؛ بل تتصل بنسخة النظام المركزية عبر عنوان HTTP/HTTPS يحدده المستخدم
في أول تشغيل.

## بناء ملف EXE المحمول

يجب أن يملك صاحب النظام شهادة Code Signing سارية بصيغة PFX/P12 وكلمة مرورها.
ضع مسار الشهادة وكلمة المرور في متغيرات البيئة (ولا تُضف الشهادة إلى Git):

```powershell
$env:WIN_CSC_LINK = "C:\secure\warehouse-code-signing.pfx"
$env:WIN_CSC_KEY_PASSWORD = Read-Host "كلمة مرور الشهادة" -MaskInput
```

ثم من جذر المشروع على Windows أو Linux:

```bash
pnpm install
pnpm desktop:dist:win
```

يتوقف البناء عمدًا إذا لم يجد شهادة، حتى لا يتم توزيع ملف غير موقّع. ينتج ملف
Windows الموقع الذي يعمل مباشرةً داخل:

```text
desktop/warehouse-management/release/Warehouse-Management-Portable-1.0.0.exe
```

لا يحتاج هذا الملف إلى تثبيت؛ يُنسخ إلى جهاز Windows ويُشغّل مباشرةً.

## بناء مثبت NSIS تقليدي

على جهاز Windows مخصص للبناء، وبعد ضبط متغيرات الشهادة نفسها:

```bash
pnpm --filter @workspace/warehouse-desktop run dist:win:installer
```

يحتاج إنشاء مثبت NSIS من Linux إلى بيئة Wine تسمح بخدمات Windows RPC، وهي
غير متاحة داخل sandbox الحالي.

إذا كانت الشهادة مخزنة في Windows Certificate Store أو على جهاز توقيع مادي،
يمكن استخدام اسمها بدل ملف PFX:

```powershell
$env:WINDOWS_CERTIFICATE_SUBJECT_NAME = "اسم الناشر كما يظهر في الشهادة"
pnpm --filter @workspace/warehouse-desktop run dist:win
pnpm --filter @workspace/warehouse-desktop run dist:win:installer
```

## التحقق من الناشر والإصدار

بعد البناء على Windows، افحص الملف المحمول والمثبت:

```powershell
pnpm --filter @workspace/warehouse-desktop run verify:win -- `
  -Path "release\Warehouse-Management-Portable-1.0.0.exe,release\Warehouse-Management-Setup-1.0.0.exe" `
  -ExpectedPublisherSubject "CN=اسم الناشر القانوني"
```

يمكن استخدام `-ExpectedCertificateThumbprint` بدل اسم الناشر، أو تمرير الخيارين
معًا لمطابقة اسم الناشر وبصمة الشهادة حرفيًا.
يفشل الفحص إذا لم يكن توقيع Authenticode صالحًا ومؤرخًا، أو لم يطابق ناشر
الشهادة (وبصمتها عند تحديدها)، أو إذا لم تطابق خصائص الملف اسم المنتج
`نظام إدارة المخزن`، واسم الشركة `Warehouse Management`، والإصدار الموجود في
`package.json`.

> التوقيع الصحيح يعرّف الناشر ويحمي الملف من التعديل، لكنه لا يضمن اختفاء
> SmartScreen فورًا مع شهادة جديدة؛ تبني Microsoft سمعة للشهادة والملف بمرور
> الوقت. شهادة EV Code Signing تعطي عادةً ثقة أولية أفضل.

## ملاحظات التشغيل

- يجب نشر الواجهة والخادم المركزيين على عنوان واحد قابل للوصول من أجهزة
  المستخدمين.
- في أول تشغيل يدخل المستخدم عنوان نسخة النظام المركزية.
- يمكن تغيير العنوان من قائمة **النظام → تغيير عنوان الخادم** أو بالاختصار
  `Ctrl+,`.
- ملفات الجلسة تبقى في الخادم المركزي، ولا تُخزن كلمات المرور داخل التطبيق.