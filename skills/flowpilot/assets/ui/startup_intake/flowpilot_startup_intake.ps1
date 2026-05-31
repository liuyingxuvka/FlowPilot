param(
    [string]$OutputDir = "",
    [string]$HeadlessConfirmText = "",
    [switch]$HeadlessCancel,
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class FlowPilotDpi {
    [DllImport("shcore.dll")]
    public static extern int SetProcessDpiAwareness(int awareness);

    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
"@

try {
    [FlowPilotDpi]::SetProcessDpiAwareness(2) | Out-Null
} catch {
    try { [FlowPilotDpi]::SetProcessDPIAware() | Out-Null } catch {}
}

Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml

function Find-FlowPilotRepoRoot {
    $cursor = [System.IO.DirectoryInfo]::new($PSScriptRoot)
    while ($null -ne $cursor) {
        $brandIcon = Join-Path $cursor.FullName "assets\brand\flowpilot-icon-default.png"
        $router = Join-Path $cursor.FullName "skills\flowpilot\assets\flowpilot_router.py"
        if ((Test-Path -LiteralPath $brandIcon) -and (Test-Path -LiteralPath $router)) {
            return $cursor.FullName
        }
        $cursor = $cursor.Parent
    }
    return $null
}

function Find-FlowPilotSkillRoot {
    $cursor = [System.IO.DirectoryInfo]::new($PSScriptRoot)
    while ($null -ne $cursor) {
        $brandIcon = Join-Path $cursor.FullName "assets\brand\flowpilot-icon-default.png"
        $router = Join-Path $cursor.FullName "assets\flowpilot_router.py"
        if ((Test-Path -LiteralPath $brandIcon) -and (Test-Path -LiteralPath $router)) {
            return $cursor.FullName
        }
        $cursor = $cursor.Parent
    }
    return $null
}

$RepoRoot = Find-FlowPilotRepoRoot
$SkillRoot = Find-FlowPilotSkillRoot
if ([string]::IsNullOrWhiteSpace($RepoRoot) -and [string]::IsNullOrWhiteSpace($SkillRoot)) {
    throw "Unable to locate FlowPilot repository or skill root from $PSScriptRoot"
}
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = $SkillRoot
}

$IconPath = if (-not [string]::IsNullOrWhiteSpace($SkillRoot)) {
    Join-Path $SkillRoot "assets\brand\flowpilot-icon-default.png"
} else {
    Join-Path $RepoRoot "assets\brand\flowpilot-icon-default.png"
}
if (-not (Test-Path -LiteralPath $IconPath)) {
    throw "Missing FlowPilot icon: $IconPath"
}

$IconUri = ([System.Uri]::new($IconPath)).AbsoluteUri
$script:StartupIntakeCompleted = $false
$script:ExitCode = 0

function Get-UtcNow {
    return [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

function Get-StartupIntakeOutputDir {
    if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
        return [System.IO.Path]::GetFullPath($OutputDir)
    }
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    return Join-Path $RepoRoot ".flowpilot\bootstrap\startup_intake\$stamp"
}

function Get-ProjectRelativePath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\') + '\'
    if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($root.Length).Replace('\', '/')
    }
    return $full
}

function Write-Utf8NoBomText([string]$Path, [string]$Value) {
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Value, $encoding)
}

function Write-JsonFile([string]$Path, [hashtable]$Payload) {
    $json = $Payload | ConvertTo-Json -Depth 20
    Write-Utf8NoBomText -Path $Path -Value ($json + [Environment]::NewLine)
}

function Get-FileSha256([string]$Path) {
    $stream = [System.IO.File]::OpenRead($Path)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($stream)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}

function New-StartupAnswerMap([bool]$AgentsEnabled) {
    return @{
        runtime_role_assistances = $(if ($AgentsEnabled) { "allow" } else { "single-agent" })
        scheduled_continuation = "manual"
        display_surface = "chat"
        provenance = "explicit_user_reply"
    }
}

function Write-StartupIntakeResult(
    [string]$Status,
    [string]$BodyText,
    [bool]$AgentsEnabled,
    [string]$Language,
    [string]$LaunchMode = "interactive_native",
    [bool]$Headless = $false,
    [bool]$FormalStartupAllowed = $true
) {
    $outDir = Get-StartupIntakeOutputDir
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $recordedAt = Get-UtcNow
    $answers = New-StartupAnswerMap $AgentsEnabled
    $source = if ($Headless) { "headless_startup_intake" } else { "native_wpf_startup_intake" }
    $receiptPath = Join-Path $outDir "startup_intake_receipt.json"
    $resultPath = Join-Path $outDir "startup_intake_result.json"

    if ($Status -eq "cancelled") {
        $receipt = @{
            schema_version = "flowpilot.startup_intake_receipt.v1"
            status = "cancelled"
            source = $source
            ui_surface = "native_wpf_startup_intake"
            launch_mode = $LaunchMode
            headless = $Headless
            formal_startup_allowed = $FormalStartupAllowed
            language = $Language
            startup_answers = $answers
            confirmed_by_user = $false
            cancelled_by_user = $true
            recorded_at = $recordedAt
        }
        Write-JsonFile $receiptPath $receipt
        $result = @{
            schema_version = "flowpilot.startup_intake_result.v1"
            status = "cancelled"
            source = $source
            launch_mode = $LaunchMode
            headless = $Headless
            formal_startup_allowed = $FormalStartupAllowed
            receipt_path = Get-ProjectRelativePath $receiptPath
            controller_visibility = "cancel_status_only"
            body_text_included = $false
            recorded_at = $recordedAt
        }
        Write-JsonFile $resultPath $result
        return $resultPath
    }

    if ([string]::IsNullOrWhiteSpace($BodyText)) {
        throw "Work request cannot be empty."
    }

    $bodyPath = Join-Path $outDir "startup_intake_body.md"
    $envelopePath = Join-Path $outDir "startup_intake_envelope.json"
    Write-Utf8NoBomText -Path $bodyPath -Value $BodyText
    $bodyHash = Get-FileSha256 $bodyPath

    $receipt = @{
        schema_version = "flowpilot.startup_intake_receipt.v1"
        status = "confirmed"
        source = $source
        ui_surface = "native_wpf_startup_intake"
        launch_mode = $LaunchMode
        headless = $Headless
        formal_startup_allowed = $FormalStartupAllowed
        language = $Language
        startup_answers = $answers
        confirmed_by_user = $true
        cancelled_by_user = $false
        body_path = Get-ProjectRelativePath $bodyPath
        body_hash = $bodyHash
        envelope_path = Get-ProjectRelativePath $envelopePath
        body_text_included = $false
        recorded_at = $recordedAt
    }
    Write-JsonFile $receiptPath $receipt

    $envelope = @{
        schema_version = "flowpilot.startup_intake_envelope.v1"
        status = "confirmed"
        source = $source
        launch_mode = $LaunchMode
        headless = $Headless
        formal_startup_allowed = $FormalStartupAllowed
        language = $Language
        startup_answers = $answers
        body_path = Get-ProjectRelativePath $bodyPath
        body_hash = $bodyHash
        receipt_path = Get-ProjectRelativePath $receiptPath
        body_visibility = "sealed_pm_only"
        controller_visibility = "envelope_only"
        controller_may_read_body = $false
        body_text_included = $false
        recorded_at = $recordedAt
    }
    Write-JsonFile $envelopePath $envelope

    $result = @{
        schema_version = "flowpilot.startup_intake_result.v1"
        status = "confirmed"
        source = $source
        launch_mode = $LaunchMode
        headless = $Headless
        formal_startup_allowed = $FormalStartupAllowed
        startup_answers = $answers
        language = $Language
        receipt_path = Get-ProjectRelativePath $receiptPath
        envelope_path = Get-ProjectRelativePath $envelopePath
        body_path = Get-ProjectRelativePath $bodyPath
        body_hash = $bodyHash
        controller_visibility = "envelope_only"
        controller_may_read_body = $false
        body_text_included = $false
        recorded_at = $recordedAt
    }
    Write-JsonFile $resultPath $result
    return $resultPath
}

if ($HeadlessCancel) {
    Write-StartupIntakeResult "cancelled" "" $true "en" "headless" $true $false | Write-Output
    exit 0
}

if (-not [string]::IsNullOrWhiteSpace($HeadlessConfirmText)) {
    Write-StartupIntakeResult "confirmed" $HeadlessConfirmText $true "en" "headless" $true $false | Write-Output
    exit 0
}

$Xaml = @"
<Window
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    Title="FlowPilot"
    Width="860"
    Height="680"
    MinWidth="780"
    MinHeight="650"
    WindowStartupLocation="CenterScreen"
    Background="#FFFFFF"
    FontFamily="Segoe UI Variable Text, Segoe UI"
    TextOptions.TextFormattingMode="Display"
    TextOptions.TextRenderingMode="ClearType"
    UseLayoutRounding="True"
    SnapsToDevicePixels="True"
    ResizeMode="CanResizeWithGrip">
  <Window.Resources>
    <SolidColorBrush x:Key="InkBrush" Color="#19121B" />
    <SolidColorBrush x:Key="MutedBrush" Color="#746677" />
    <SolidColorBrush x:Key="LineBrush" Color="#EEE2EF" />
    <SolidColorBrush x:Key="PanelBrush" Color="#FFFFFF" />
    <SolidColorBrush x:Key="FieldBrush" Color="#FFFFFF" />
    <SolidColorBrush x:Key="AccentBrush" Color="#8A5AD0" />
    <SolidColorBrush x:Key="AccentHoverBrush" Color="#7A49C3" />
    <SolidColorBrush x:Key="AccentPressedBrush" Color="#6537A7" />
    <SolidColorBrush x:Key="AccentSoftBrush" Color="#F0E7FA" />
    <SolidColorBrush x:Key="AccentLineBrush" Color="#D8C6EE" />
    <SolidColorBrush x:Key="AccentTextBrush" Color="#61309A" />

    <Style x:Key="PrimaryButton" TargetType="Button">
      <Setter Property="MinWidth" Value="132" />
      <Setter Property="Height" Value="44" />
      <Setter Property="Padding" Value="20,0" />
      <Setter Property="Foreground" Value="#FFFFFF" />
      <Setter Property="Background" Value="{StaticResource AccentBrush}" />
      <Setter Property="BorderBrush" Value="{StaticResource AccentBrush}" />
      <Setter Property="BorderThickness" Value="1" />
      <Setter Property="FontWeight" Value="SemiBold" />
      <Setter Property="Cursor" Value="Hand" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border
                x:Name="ButtonBorder"
                Background="{TemplateBinding Background}"
                BorderBrush="{TemplateBinding BorderBrush}"
                BorderThickness="{TemplateBinding BorderThickness}"
                CornerRadius="8">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="ButtonBorder" Property="Background" Value="{StaticResource AccentHoverBrush}" />
                <Setter TargetName="ButtonBorder" Property="BorderBrush" Value="{StaticResource AccentHoverBrush}" />
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="ButtonBorder" Property="Background" Value="{StaticResource AccentPressedBrush}" />
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="IconButton" TargetType="Button">
      <Setter Property="Width" Value="38" />
      <Setter Property="Height" Value="38" />
      <Setter Property="Foreground" Value="{StaticResource AccentTextBrush}" />
      <Setter Property="Background" Value="#FFFFFF" />
      <Setter Property="BorderBrush" Value="{StaticResource AccentLineBrush}" />
      <Setter Property="BorderThickness" Value="1" />
      <Setter Property="FontSize" Value="18" />
      <Setter Property="FontWeight" Value="SemiBold" />
      <Setter Property="Cursor" Value="Hand" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border
                x:Name="ButtonBorder"
                Background="{TemplateBinding Background}"
                BorderBrush="{TemplateBinding BorderBrush}"
                BorderThickness="{TemplateBinding BorderThickness}"
                CornerRadius="8">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="ButtonBorder" Property="Background" Value="{StaticResource AccentSoftBrush}" />
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="ButtonBorder" Property="Background" Value="#E7D8F6" />
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="LinkButton" TargetType="Button">
      <Setter Property="Padding" Value="0" />
      <Setter Property="Foreground" Value="{StaticResource AccentTextBrush}" />
      <Setter Property="Background" Value="Transparent" />
      <Setter Property="BorderBrush" Value="Transparent" />
      <Setter Property="BorderThickness" Value="0" />
      <Setter Property="FontSize" Value="12.5" />
      <Setter Property="FontWeight" Value="SemiBold" />
      <Setter Property="Cursor" Value="Hand" />
      <Setter Property="HorizontalContentAlignment" Value="Left" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <ContentPresenter HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="Center" />
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="LanguageChoice" TargetType="RadioButton">
      <Setter Property="Height" Value="30" />
      <Setter Property="MinWidth" Value="68" />
      <Setter Property="Foreground" Value="#6D5F70" />
      <Setter Property="FontSize" Value="12.5" />
      <Setter Property="FontWeight" Value="SemiBold" />
      <Setter Property="Cursor" Value="Hand" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="RadioButton">
            <Border
                x:Name="ChoiceBorder"
                Background="Transparent"
                BorderBrush="Transparent"
                BorderThickness="1"
                CornerRadius="15"
                Padding="10,0">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="True">
                <Setter TargetName="ChoiceBorder" Property="Background" Value="{StaticResource AccentSoftBrush}" />
                <Setter TargetName="ChoiceBorder" Property="BorderBrush" Value="{StaticResource AccentLineBrush}" />
                <Setter Property="Foreground" Value="{StaticResource AccentTextBrush}" />
              </Trigger>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="ChoiceBorder" Property="BorderBrush" Value="{StaticResource AccentLineBrush}" />
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="ScrollBarPageButton" TargetType="RepeatButton">
      <Setter Property="Focusable" Value="False" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="RepeatButton">
            <Border Background="Transparent" />
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="ScrollBarThumb" TargetType="Thumb">
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Thumb">
            <Border Background="#D9B7DA" CornerRadius="4" />
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style TargetType="ScrollBar">
      <Setter Property="Width" Value="10" />
      <Setter Property="Background" Value="Transparent" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="ScrollBar">
            <Grid Background="Transparent" Width="10">
              <Track x:Name="PART_Track" IsDirectionReversed="True">
                <Track.DecreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageUpCommand" Style="{StaticResource ScrollBarPageButton}" />
                </Track.DecreaseRepeatButton>
                <Track.Thumb>
                  <Thumb Style="{StaticResource ScrollBarThumb}" />
                </Track.Thumb>
                <Track.IncreaseRepeatButton>
                  <RepeatButton Command="ScrollBar.PageDownCommand" Style="{StaticResource ScrollBarPageButton}" />
                </Track.IncreaseRepeatButton>
              </Track>
            </Grid>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="SwitchToggle" TargetType="ToggleButton">
      <Setter Property="Width" Value="88" />
      <Setter Property="Height" Value="40" />
      <Setter Property="Cursor" Value="Hand" />
      <Setter Property="Focusable" Value="True" />
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="ToggleButton">
            <Grid Width="88" Height="40" SnapsToDevicePixels="True">
              <Border
                  x:Name="Track"
                  Background="{StaticResource AccentSoftBrush}"
                  BorderBrush="{StaticResource AccentLineBrush}"
                  BorderThickness="1"
                  CornerRadius="20" />
              <TextBlock
                  x:Name="StateLabel"
                  Text="ON"
                  Foreground="{StaticResource AccentTextBrush}"
                  FontSize="10"
                  FontWeight="Bold"
                  HorizontalAlignment="Left"
                  VerticalAlignment="Center"
                  Margin="15,0,0,0" />
              <Ellipse
                  x:Name="Knob"
                  Width="30"
                  Height="30"
                  Fill="#FFFFFF"
                  Stroke="#E8C8E8"
                  StrokeThickness="1"
                  HorizontalAlignment="Right"
                  VerticalAlignment="Center"
                  Margin="4" />
            </Grid>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="False">
                <Setter TargetName="Track" Property="Background" Value="#D9D9D9" />
                <Setter TargetName="Track" Property="BorderBrush" Value="#B8B8B8" />
                <Setter TargetName="StateLabel" Property="Text" Value="OFF" />
                <Setter TargetName="StateLabel" Property="Foreground" Value="#4F4F4F" />
                <Setter TargetName="StateLabel" Property="HorizontalAlignment" Value="Right" />
                <Setter TargetName="StateLabel" Property="Margin" Value="0,0,12,0" />
                <Setter TargetName="Knob" Property="HorizontalAlignment" Value="Left" />
                <Setter TargetName="Knob" Property="Stroke" Value="#CFCFCF" />
              </Trigger>
              <Trigger Property="IsKeyboardFocused" Value="True">
                <Setter TargetName="Track" Property="BorderBrush" Value="{StaticResource AccentBrush}" />
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>

  <Grid Background="{StaticResource PanelBrush}" ClipToBounds="True">
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto" />
          <RowDefinition Height="*" />
          <RowDefinition Height="Auto" />
        </Grid.RowDefinitions>

        <Grid Grid.Row="0" Margin="38,44,38,24">
          <Grid.ColumnDefinitions>
            <ColumnDefinition Width="Auto" />
            <ColumnDefinition Width="*" />
            <ColumnDefinition Width="Auto" />
          </Grid.ColumnDefinitions>

          <Image
              Grid.Column="0"
              Source="$IconUri"
              Width="56"
              Height="56"
              RenderOptions.BitmapScalingMode="HighQuality"
              Margin="0,0,16,0"
              VerticalAlignment="Center" />

          <StackPanel Grid.Column="1" VerticalAlignment="Center">
            <TextBlock
                x:Name="TitleText"
                Text="FlowPilot"
                Foreground="{StaticResource InkBrush}"
                FontFamily="Segoe UI Variable Display, Segoe UI"
                FontSize="28"
                FontWeight="SemiBold" />
          </StackPanel>

          <Grid Grid.Column="2" VerticalAlignment="Top">
            <Button
                x:Name="SettingsButton"
                Style="{StaticResource IconButton}"
                Content="⚙" />
            <Popup
                x:Name="SettingsPopup"
                Placement="Bottom"
                HorizontalOffset="-274"
                VerticalOffset="8"
                StaysOpen="False"
                AllowsTransparency="True"
                PopupAnimation="Fade">
              <Border
                  Width="312"
                  Background="#FFFFFF"
                  BorderBrush="{StaticResource AccentLineBrush}"
                  BorderThickness="1"
                  CornerRadius="8"
                  Padding="16">
                <StackPanel>
                  <TextBlock
                      x:Name="SettingsTitle"
                      Text="Settings"
                      Foreground="{StaticResource InkBrush}"
                      FontSize="14"
                      FontWeight="SemiBold"
                      Margin="0,0,0,12" />
                  <TextBlock
                      x:Name="LanguageLabel"
                      Text="Language"
                      Foreground="{StaticResource MutedBrush}"
                      FontSize="12.5"
                      FontWeight="SemiBold"
                      Margin="0,0,0,7" />
                  <Border Background="Transparent" Padding="0" HorizontalAlignment="Left" Margin="0,0,0,16">
                    <StackPanel Orientation="Horizontal">
                      <RadioButton x:Name="EnglishLanguage" GroupName="Language" IsChecked="True" Content="English" Style="{StaticResource LanguageChoice}" />
                      <RadioButton x:Name="ChineseLanguage" GroupName="Language" Content="中文" Style="{StaticResource LanguageChoice}" />
                    </StackPanel>
                  </Border>
                  <Border BorderBrush="{StaticResource LineBrush}" BorderThickness="0,1,0,0" Padding="0,14,0,0">
                    <StackPanel>
                      <TextBlock
                          x:Name="SupportTitle"
                          Text="Support developer"
                          Foreground="{StaticResource InkBrush}"
                          FontSize="13"
                          FontWeight="SemiBold" />
                      <TextBlock
                          x:Name="SupportBody"
                          Text="Buy the developer a coffee via PayPal."
                          Foreground="{StaticResource MutedBrush}"
                          FontSize="12.5"
                          TextWrapping="Wrap"
                          Margin="0,5,0,4" />
                      <Button
                          x:Name="SupportLinkButton"
                          Content="https://paypal.me/Yingxuliu"
                          Style="{StaticResource LinkButton}" />
                      <TextBlock
                          x:Name="SupportNote"
                          Text="Support is voluntary and does not purchase technical support, warranty, priority service, commercial rights, or feature requests."
                          Foreground="{StaticResource MutedBrush}"
                          FontSize="11.5"
                          TextWrapping="Wrap"
                          Margin="0,8,0,0" />
                    </StackPanel>
                  </Border>
                </StackPanel>
              </Border>
            </Popup>
          </Grid>
        </Grid>

        <ScrollViewer
            Grid.Row="1"
            VerticalScrollBarVisibility="Auto"
            HorizontalScrollBarVisibility="Disabled"
            Padding="38,0,30,0">
          <Grid MinHeight="350">
            <Grid.ColumnDefinitions>
              <ColumnDefinition Width="*" MinWidth="330" />
              <ColumnDefinition Width="*" MinWidth="330" />
            </Grid.ColumnDefinitions>
            <Grid
                Grid.Column="0"
                Margin="0,0,18,0">
              <StackPanel>
                <DockPanel Margin="0,0,0,10">
                  <TextBlock
                      x:Name="RequestLabel"
                      Text="Work request"
                      Foreground="{StaticResource InkBrush}"
                      FontSize="14"
                      FontWeight="SemiBold"
                      DockPanel.Dock="Left" />
                </DockPanel>

                <Grid>
                  <TextBox
                      x:Name="WorkRequest"
                      MinHeight="318"
                      AcceptsReturn="True"
                      TextWrapping="Wrap"
                      VerticalScrollBarVisibility="Auto"
                      BorderBrush="#E2C7E2"
                      BorderThickness="1"
                      Background="{StaticResource FieldBrush}"
                      Foreground="{StaticResource InkBrush}"
                      FontSize="14"
                      Padding="14"
                      SpellCheck.IsEnabled="True" />
                  <TextBlock
                      x:Name="PlaceholderText"
                      Text="Write the instructions you want the AI to follow."
                      Foreground="#9A869E"
                      FontSize="14"
                      Margin="18,15,18,0"
                      TextWrapping="Wrap"
                      IsHitTestVisible="False" />
                </Grid>

              </StackPanel>
            </Grid>

            <StackPanel
                Grid.Column="1"
                VerticalAlignment="Top"
                Margin="6,30,0,0">
                <Grid MinHeight="82" Margin="0,0,0,26">
                  <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*" />
                    <ColumnDefinition Width="Auto" />
                  </Grid.ColumnDefinitions>
                  <StackPanel Grid.Column="0" VerticalAlignment="Center">
                    <TextBlock x:Name="AgentsTitle" Text="Background collaboration" Foreground="{StaticResource InkBrush}" FontSize="14" FontWeight="SemiBold" />
                    <TextBlock x:Name="AgentsBody" Text="Allow FlowPilot to use this environment's supported background workers for isolated role work." Foreground="{StaticResource MutedBrush}" FontSize="12.5" TextWrapping="Wrap" Margin="0,5,16,0" />
                  </StackPanel>
                  <ToggleButton x:Name="AgentsToggle" Grid.Column="1" IsChecked="True" Style="{StaticResource SwitchToggle}" VerticalAlignment="Center" />
                </Grid>
            </StackPanel>
          </Grid>
        </ScrollViewer>

        <Grid Grid.Row="2" Margin="38,34,38,26">
          <Grid.RowDefinitions>
            <RowDefinition Height="Auto" />
            <RowDefinition Height="Auto" />
          </Grid.RowDefinitions>
          <TextBlock
              x:Name="StatusText"
              Grid.Row="1"
              HorizontalAlignment="Center"
              Foreground="{StaticResource MutedBrush}"
              FontSize="12.5"
              Margin="0,10,0,0" />
          <Button
              x:Name="ConfirmButton"
              Grid.Row="0"
              HorizontalAlignment="Center"
              Style="{StaticResource PrimaryButton}"
              Content="Confirm" />
        </Grid>
      </Grid>
</Window>
"@

$Reader = [System.Xml.XmlReader]::Create([System.IO.StringReader]::new($Xaml))
$Window = [Windows.Markup.XamlReader]::Load($Reader)
$Window.Icon = [System.Windows.Media.Imaging.BitmapImage]::new([System.Uri]::new($IconPath))

$Names = @(
    "SettingsButton", "SettingsPopup", "EnglishLanguage", "ChineseLanguage",
    "SettingsTitle", "LanguageLabel", "SupportTitle", "SupportBody",
    "SupportLinkButton", "SupportNote", "TitleText", "RequestLabel",
    "WorkRequest", "PlaceholderText", "AgentsTitle", "AgentsBody",
    "AgentsToggle", "ConfirmButton", "StatusText"
)

$Ui = @{}
foreach ($Name in $Names) {
    $Ui[$Name] = $Window.FindName($Name)
}

$Copy = @{
    en = @{
        Window = "FlowPilot"
        Title = "FlowPilot"
        SettingsTooltip = "Settings"
        SettingsTitle = "Settings"
        LanguageLabel = "Language"
        SupportTitle = "Support developer"
        SupportBody = "Buy the developer a coffee via PayPal."
        SupportNote = "Support is voluntary and does not purchase technical support, warranty, priority service, commercial rights, or feature requests."
        RequestLabel = "Work request"
        Placeholder = "Write the instructions you want the AI to follow."
        AgentsTitle = "Background collaboration"
        AgentsBody = "Allow FlowPilot to use this environment's supported background workers for isolated role work."
        Confirm = "Confirm"
        Confirmed = "Startup intake recorded."
    }
    zh = @{
        Window = "FlowPilot"
        Title = "FlowPilot"
        SettingsTooltip = "设置"
        SettingsTitle = "设置"
        LanguageLabel = "语言"
        SupportTitle = "支持开发者"
        SupportBody = "通过 PayPal 请开发者喝杯咖啡。"
        SupportNote = "支持是自愿的，不购买技术支持、保修、优先服务、商业权利或功能请求承诺。"
        RequestLabel = "工作要求"
        Placeholder = "请写下给 AI 的工作目标和具体命令。"
        AgentsTitle = "后台协作"
        AgentsBody = "允许 FlowPilot 使用当前环境支持的后台工作者处理隔离的角色任务。"
        Confirm = "确认"
        Confirmed = "启动注入已记录。"
    }
}

function Get-Language {
    if ($Ui.ChineseLanguage.IsChecked) { return "zh" }
    return "en"
}

function Update-Placeholder {
    if ([string]::IsNullOrWhiteSpace($Ui.WorkRequest.Text)) {
        $Ui.PlaceholderText.Visibility = [System.Windows.Visibility]::Visible
    } else {
        $Ui.PlaceholderText.Visibility = [System.Windows.Visibility]::Collapsed
    }
}

function Apply-Language {
    $Lang = Get-Language
    $T = $Copy[$Lang]
    $Window.Title = $T.Window
    $Ui.TitleText.Text = $T.Title
    $Ui.SettingsButton.ToolTip = $T.SettingsTooltip
    $Ui.SettingsTitle.Text = $T.SettingsTitle
    $Ui.LanguageLabel.Text = $T.LanguageLabel
    $Ui.SupportTitle.Text = $T.SupportTitle
    $Ui.SupportBody.Text = $T.SupportBody
    $Ui.SupportNote.Text = $T.SupportNote
    $Ui.RequestLabel.Text = $T.RequestLabel
    $Ui.PlaceholderText.Text = $T.Placeholder
    $Ui.AgentsTitle.Text = $T.AgentsTitle
    $Ui.AgentsBody.Text = $T.AgentsBody
    $Ui.ConfirmButton.Content = $T.Confirm
    $Ui.StatusText.Text = ""
}

$SupportUrl = "https://paypal.me/Yingxuliu"
$Ui.SettingsPopup.PlacementTarget = $Ui.SettingsButton
$Ui.SettingsButton.Add_Click({
    $Ui.SettingsPopup.IsOpen = -not $Ui.SettingsPopup.IsOpen
})
$Ui.SupportLinkButton.Add_Click({
    try {
        Start-Process $SupportUrl
    } catch {
        $Ui.StatusText.Text = $_.Exception.Message
    }
})
$Ui.EnglishLanguage.Add_Checked({ Apply-Language })
$Ui.ChineseLanguage.Add_Checked({ Apply-Language })
$Ui.WorkRequest.Add_TextChanged({ Update-Placeholder })
$Ui.ConfirmButton.Add_Click({
    $Lang = Get-Language
    try {
        $resultPath = Write-StartupIntakeResult `
            "confirmed" `
            $Ui.WorkRequest.Text `
            ([bool]$Ui.AgentsToggle.IsChecked) `
            $Lang
        $script:StartupIntakeCompleted = $true
        $script:ExitCode = 0
        $Ui.StatusText.Text = $Copy[$Lang].Confirmed
        $Window.Tag = $resultPath
        $Window.Close()
    } catch {
        $Ui.StatusText.Text = $_.Exception.Message
    }
})

$Window.Add_Closing({
    if (-not $script:StartupIntakeCompleted -and -not $SmokeTest) {
        try {
            Write-StartupIntakeResult `
                "cancelled" `
                "" `
                ([bool]$Ui.AgentsToggle.IsChecked) `
                (Get-Language) | Out-Null
            $script:ExitCode = 0
        } catch {
            $script:ExitCode = 1
        }
    }
})

Apply-Language
Update-Placeholder

if ($SmokeTest) {
    $Window.Close()
    "UI_SMOKE_OK"
    exit 0
}

$Window.ShowDialog() | Out-Null
exit $script:ExitCode
