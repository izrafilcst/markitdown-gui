; Script do Inno Setup para o MarkItDown.
;
; Compilado por installer/build_setup.py, que passa as variaveis abaixo
; com /D. Nao ha caminho fixo aqui, para o script funcionar em qualquer
; copia do repositorio.
;
; Por que Inno Setup e nao um executavel unico do PyInstaller: medido
; nesta maquina, um onefile grande trava na descompactacao para o
; temporario e nunca abre janela. O Inno usa o mecanismo de instalacao
; padrao do Windows, que nao passa por isso.
;
; O arquivo e ASCII de proposito. Acento em .iss exige UTF-8 com BOM, e
; um erro de codificacao aqui so aparece na tela do usuario final.

#ifndef Versao
  #define Versao "1.0.0"
#endif
#ifndef Carga
  #error "Defina /DCarga com a pasta dist/MarkItDown"
#endif
#ifndef Icone
  #error "Defina /DIcone com o caminho do icone.ico"
#endif
#ifndef Saida
  #define Saida "."
#endif
#ifndef LimitePasta
  #define LimitePasta "150"
#endif

#define Nome "MarkItDown"
#define Autor "MarkItDown"
#define Executavel "MarkItDown.exe"

[Setup]
AppId={{8F3A1C42-6E7B-4D59-9C21-5B0E7A4D8F13}
AppName={#Nome}
AppVersion={#Versao}
AppVerName={#Nome} {#Versao}
AppPublisher={#Autor}
VersionInfoVersion={#Versao}

; Instala para o usuario atual. Sem elevacao, sem caixa de permissao.
; Converter um PDF nao deveria exigir senha de administrador.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#Nome}
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
AllowNoIcons=yes

OutputDir={#Saida}
OutputBaseFilename=MarkItDown-Setup
SetupIconFile={#Icone}
UninstallDisplayIcon={app}\{#Executavel}
UninstallDisplayName={#Nome} {#Versao}

WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; O instalador mexe no PATH quando o usuario pede, e o Windows precisa
; ser avisado para nao exigir logoff.
ChangesEnvironment=yes

[Languages]
Name: "brazilian"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"
Name: "addtopath"; Description: "Adicionar ao PATH, para chamar pelo terminal"; \
  GroupDescription: "Opcoes"; Flags: unchecked

[Files]
Source: "{#Carga}\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nome}"; Filename: "{app}\{#Executavel}"
Name: "{group}\Desinstalar {#Nome}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Executavel}"; \
  Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Tasks: addtopath; Check: FaltaNoPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#Executavel}"; \
  Description: "{cm:LaunchProgram,{#StringChange(Nome, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[Code]
function LimiteDaPasta(): Integer;
begin
  { Vem de /DLimitePasta, calculado pelo build_setup.py a partir do
    arquivo de caminho mais longo dentro da carga. Hoje o campeao e
    _internal\lxml\isoschematron\...\iso_schematron_skeleton_for_xslt1.xsl,
    com 101 caracteres. Somado a pasta de destino, o total precisa caber
    nos 260 caracteres do Windows. }
  Result := {#LimitePasta};
end;

function PastaCabe(Pasta: string): Boolean;
begin
  Result := Length(Pasta) <= LimiteDaPasta();
end;

function AvisoDePastaLonga(Pasta: string): string;
begin
  Result :=
    'O caminho escolhido e longo demais para este programa.' + #13#10#13#10 +
    'Escolhido: ' + IntToStr(Length(Pasta)) + ' caracteres.' + #13#10 +
    'Maximo   : ' + IntToStr(LimiteDaPasta()) + ' caracteres.' + #13#10#13#10 +
    'O Windows limita caminhos a 260 caracteres, e alguns arquivos deste ' +
    'programa ja usam mais de cem. Escolha uma pasta mais curta, por ' +
    'exemplo a pasta padrao.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    { Recusar aqui, e nao no meio da copia. Estourar o limite durante a
      instalacao faz o Inno desfazer tudo e mostrar "MoveFile falhou;
      codigo 3", que nao diz nada ao usuario. }
    if not PastaCabe(WizardDirValue) then
    begin
      MsgBox(AvisoDePastaLonga(WizardDirValue), mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  { Rede de seguranca para instalacao silenciosa, onde nenhuma pagina do
    assistente e mostrada e NextButtonClick nunca roda. }
  Result := '';
  if not PastaCabe(ExpandConstant('{app}')) then
    Result := AvisoDePastaLonga(ExpandConstant('{app}'));
end;

function FaltaNoPath(Pasta: string): Boolean;
var
  Atual: string;
begin
  { Sem esta checagem, reinstalar acrescenta a mesma pasta de novo e o
    PATH do usuario incha a cada instalacao. Os pontos e virgula nas
    pontas evitam casar com um caminho que apenas comece igual. }
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Atual) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Pasta) + ';', ';' + Uppercase(Atual) + ';') = 0;
end;

procedure LimparDoPath();
var
  Atual: string;
  Alvo: string;
  Posicao: Integer;
begin
  { Desinstalar precisa devolver o PATH como estava. Deixar entrada morta
    apontando para pasta apagada e um dos defeitos mais comuns de
    instalador ruim. }
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Atual) then
    exit;
  Alvo := ';' + Uppercase(ExpandConstant('{app}'));
  Posicao := Pos(Alvo, ';' + Uppercase(Atual));
  if Posicao > 0 then
  begin
    Delete(Atual, Posicao, Length(Alvo));
    RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Atual);
  end;
end;

procedure CurUninstallStepChanged(CurStep: TUninstallStep);
begin
  if CurStep = usUninstall then
    LimparDoPath();
end;
