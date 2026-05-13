param(
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

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$IconPath = Join-Path $RepoRoot "assets\brand\flowpilot-icon-default.png"
if (-not (Test-Path -LiteralPath $IconPath)) {
    throw "Missing FlowPilot icon: $IconPath"
}

$IconUri = ([System.Uri]::new($IconPath)).AbsoluteUri

$Xaml = @"
<Window
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    Title="FlowPilot Startup Intake"
    Width="800"
    Height="640"
    MinWidth="680"
    MinHeight="560"
    WindowStartupLocation="CenterScreen"
    Background="#FFFDF7"
    FontFamily="Segoe UI Variable Text, Segoe UI"
    TextOptions.TextFormattingMode="Display"
    TextOptions.TextRenderingMode="ClearType"
    UseLayoutRounding="True"
    SnapsToDevicePixels="True"
    ResizeMode="CanResizeWithGrip">
  <Window.Resources>
    <SolidColorBrush x:Key="InkBrush" Color="#141414" />
    <SolidColorBrush x:Key="MutedBrush" Color="#706A62" />
    <SolidColorBrush x:Key="LineBrush" Color="#E2DCD2" />
    <SolidColorBrush x:Key="PanelBrush" Color="#FFFFFF" />
    <SolidColorBrush x:Key="FieldBrush" Color="#FBFAF7" />
    <SolidColorBrush x:Key="AccentBrush" Color="#B9821D" />

    <Style x:Key="PrimaryButton" TargetType="Button">
      <Setter Property="MinWidth" Value="132" />
      <Setter Property="Height" Value="44" />
      <Setter Property="Padding" Value="20,0" />
      <Setter Property="Foreground" Value="#FFFDF7" />
      <Setter Property="Background" Value="#141414" />
      <Setter Property="BorderBrush" Value="#141414" />
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
                <Setter TargetName="ButtonBorder" Property="Background" Value="#2A2723" />
                <Setter TargetName="ButtonBorder" Property="BorderBrush" Value="#2A2723" />
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="ButtonBorder" Property="Background" Value="#000000" />
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="LanguageChoice" TargetType="RadioButton">
      <Setter Property="Height" Value="30" />
      <Setter Property="MinWidth" Value="68" />
      <Setter Property="Foreground" Value="#625C55" />
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
                <Setter TargetName="ChoiceBorder" Property="Background" Value="#141414" />
                <Setter TargetName="ChoiceBorder" Property="BorderBrush" Value="#141414" />
                <Setter Property="Foreground" Value="#FFFDF7" />
              </Trigger>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="ChoiceBorder" Property="BorderBrush" Value="#CFC7BA" />
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
            <Border Background="#CBC3B8" CornerRadius="4" />
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
                  Background="#141414"
                  BorderBrush="#141414"
                  BorderThickness="1"
                  CornerRadius="20" />
              <TextBlock
                  x:Name="StateLabel"
                  Text="ON"
                  Foreground="#FFFDF7"
                  FontSize="10"
                  FontWeight="Bold"
                  HorizontalAlignment="Left"
                  VerticalAlignment="Center"
                  Margin="15,0,0,0" />
              <Ellipse
                  x:Name="Knob"
                  Width="30"
                  Height="30"
                  Fill="#FFFDF7"
                  Stroke="#D8CFC1"
                  StrokeThickness="1"
                  HorizontalAlignment="Right"
                  VerticalAlignment="Center"
                  Margin="4" />
            </Grid>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="False">
                <Setter TargetName="Track" Property="Background" Value="#D6D0C7" />
                <Setter TargetName="Track" Property="BorderBrush" Value="#A69E94" />
                <Setter TargetName="StateLabel" Property="Text" Value="OFF" />
                <Setter TargetName="StateLabel" Property="Foreground" Value="#514B44" />
                <Setter TargetName="StateLabel" Property="HorizontalAlignment" Value="Right" />
                <Setter TargetName="StateLabel" Property="Margin" Value="0,0,12,0" />
                <Setter TargetName="Knob" Property="HorizontalAlignment" Value="Left" />
              </Trigger>
              <Trigger Property="IsKeyboardFocused" Value="True">
                <Setter TargetName="Track" Property="BorderBrush" Value="#B9821D" />
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

        <Grid Grid.Row="0" Margin="36,32,36,22">
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
                Text="Start FlowPilot"
                Foreground="{StaticResource InkBrush}"
                FontFamily="Segoe UI Variable Display, Segoe UI"
                FontSize="30"
                FontWeight="SemiBold" />
          </StackPanel>

          <Border
              Grid.Column="2"
              BorderBrush="{StaticResource LineBrush}"
              BorderThickness="1"
              CornerRadius="17"
              Padding="10,0"
              Height="36"
              VerticalAlignment="Top"
              Background="#FFFDF7">
            <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
              <Viewbox Width="18" Height="18" Margin="0,0,7,0">
                <Canvas Width="24" Height="24">
                  <Ellipse Width="18" Height="18" Canvas.Left="3" Canvas.Top="3" Stroke="#141414" StrokeThickness="1.5" />
                  <Line X1="4" Y1="9" X2="20" Y2="9" Stroke="#141414" StrokeThickness="1.5" />
                  <Line X1="4" Y1="15" X2="20" Y2="15" Stroke="#141414" StrokeThickness="1.5" />
                  <Path Data="M12 3 C15 6 15 18 12 21" Stroke="#141414" StrokeThickness="1.5" Fill="{x:Null}" />
                  <Path Data="M12 3 C9 6 9 18 12 21" Stroke="#141414" StrokeThickness="1.5" Fill="{x:Null}" />
                </Canvas>
              </Viewbox>
              <Border Background="#F2EFE9" CornerRadius="17" Padding="2">
                <StackPanel Orientation="Horizontal">
                  <RadioButton x:Name="EnglishLanguage" GroupName="Language" IsChecked="True" Content="English" Style="{StaticResource LanguageChoice}" />
                  <RadioButton x:Name="ChineseLanguage" GroupName="Language" Content="中文" Style="{StaticResource LanguageChoice}" />
                </StackPanel>
              </Border>
            </StackPanel>
          </Border>
        </Grid>

        <ScrollViewer
            Grid.Row="1"
            VerticalScrollBarVisibility="Auto"
            HorizontalScrollBarVisibility="Disabled"
            Padding="36,0,28,0">
          <StackPanel>
            <Border
                BorderBrush="#E8E2DA"
                BorderThickness="1"
                CornerRadius="8"
                Background="#FFFDF7"
                Padding="18"
                Margin="0,0,0,18">
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
                      MinHeight="230"
                      AcceptsReturn="True"
                      TextWrapping="Wrap"
                      VerticalScrollBarVisibility="Auto"
                      BorderBrush="#C9BFAF"
                      BorderThickness="1"
                      Background="{StaticResource FieldBrush}"
                      Foreground="{StaticResource InkBrush}"
                      FontSize="14"
                      Padding="14"
                      SpellCheck.IsEnabled="True" />
                  <TextBlock
                      x:Name="PlaceholderText"
                      Text="Write the instructions you want the AI to follow."
                      Foreground="#8D857A"
                      FontSize="14"
                      Margin="18,15,18,0"
                      TextWrapping="Wrap"
                      IsHitTestVisible="False" />
                </Grid>

              </StackPanel>
            </Border>

            <Border
                BorderBrush="{StaticResource LineBrush}"
                BorderThickness="1"
                CornerRadius="8"
                Background="#FFFDF7"
                Margin="0,0,0,18">
              <StackPanel>
                <Grid MinHeight="78" Margin="18,15">
                  <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*" />
                    <ColumnDefinition Width="Auto" />
                  </Grid.ColumnDefinitions>
                  <StackPanel Grid.Column="0" VerticalAlignment="Center">
                    <TextBlock x:Name="AgentsTitle" Text="Background agents" Foreground="{StaticResource InkBrush}" FontSize="14" FontWeight="SemiBold" />
                    <TextBlock x:Name="AgentsBody" Text="Allow the six-role crew when the host supports it." Foreground="{StaticResource MutedBrush}" FontSize="12.5" TextWrapping="Wrap" Margin="0,5,16,0" />
                  </StackPanel>
                  <ToggleButton x:Name="AgentsToggle" Grid.Column="1" IsChecked="True" Style="{StaticResource SwitchToggle}" VerticalAlignment="Center" />
                </Grid>

                <Border Height="1" Background="{StaticResource LineBrush}" />

                <Grid MinHeight="78" Margin="18,15">
                  <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*" />
                    <ColumnDefinition Width="Auto" />
                  </Grid.ColumnDefinitions>
                  <StackPanel Grid.Column="0" VerticalAlignment="Center">
                    <TextBlock x:Name="ContinuationTitle" Text="Scheduled continuation" Foreground="{StaticResource InkBrush}" FontSize="14" FontWeight="SemiBold" />
                    <TextBlock x:Name="ContinuationBody" Text="Allow heartbeat or manual-resume setup for long work." Foreground="{StaticResource MutedBrush}" FontSize="12.5" TextWrapping="Wrap" Margin="0,5,16,0" />
                  </StackPanel>
                  <ToggleButton x:Name="ContinuationToggle" Grid.Column="1" IsChecked="True" Style="{StaticResource SwitchToggle}" VerticalAlignment="Center" />
                </Grid>

                <Border Height="1" Background="{StaticResource LineBrush}" />

                <Grid MinHeight="78" Margin="18,15">
                  <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="*" />
                    <ColumnDefinition Width="Auto" />
                  </Grid.ColumnDefinitions>
                  <StackPanel Grid.Column="0" VerticalAlignment="Center">
                    <TextBlock x:Name="CockpitTitle" Text="Cockpit UI" Foreground="{StaticResource InkBrush}" FontSize="14" FontWeight="SemiBold" />
                    <TextBlock x:Name="CockpitBody" Text="Open the visual control surface instead of chat-only route signs." Foreground="{StaticResource MutedBrush}" FontSize="12.5" TextWrapping="Wrap" Margin="0,5,16,0" />
                  </StackPanel>
                  <ToggleButton x:Name="CockpitToggle" Grid.Column="1" IsChecked="True" Style="{StaticResource SwitchToggle}" VerticalAlignment="Center" />
                </Grid>
              </StackPanel>
            </Border>
          </StackPanel>
        </ScrollViewer>

        <Grid Grid.Row="2" Margin="36,4,36,30">
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
              Content="Confirm intake" />
        </Grid>
      </Grid>
</Window>
"@

$Reader = [System.Xml.XmlReader]::Create([System.IO.StringReader]::new($Xaml))
$Window = [Windows.Markup.XamlReader]::Load($Reader)

$Names = @(
    "EnglishLanguage", "ChineseLanguage", "TitleText", "RequestLabel",
    "WorkRequest", "PlaceholderText", "AgentsTitle", "AgentsBody",
    "ContinuationTitle", "ContinuationBody", "CockpitTitle", "CockpitBody",
    "ConfirmButton", "StatusText"
)

$Ui = @{}
foreach ($Name in $Names) {
    $Ui[$Name] = $Window.FindName($Name)
}

$Copy = @{
    en = @{
        Window = "FlowPilot Startup Intake"
        Title = "Start FlowPilot"
        RequestLabel = "Work request"
        Placeholder = "Write the instructions you want the AI to follow."
        AgentsTitle = "Background agents"
        AgentsBody = "Allow the six-role crew when the host supports it."
        ContinuationTitle = "Scheduled continuation"
        ContinuationBody = "Allow heartbeat or manual-resume setup for long work."
        CockpitTitle = "Cockpit UI"
        CockpitBody = "Open the visual control surface instead of chat-only route signs."
        Confirm = "Confirm intake"
        Confirmed = "Intake preview confirmed. No FlowPilot process has been started."
    }
    zh = @{
        Window = "FlowPilot 启动注入"
        Title = "启动 FlowPilot"
        RequestLabel = "工作要求"
        Placeholder = "请写下给 AI 的工作目标和具体命令。"
        AgentsTitle = "后台智能体"
        AgentsBody = "宿主支持时允许启用六角色团队。"
        ContinuationTitle = "定时继续"
        ContinuationBody = "允许为长任务设置心跳或手动恢复。"
        CockpitTitle = "Cockpit UI"
        CockpitBody = "打开可视化控制台，而不是只用聊天路线标识。"
        Confirm = "确认注入"
        Confirmed = "注入预览已确认。当前没有启动 FlowPilot 流程。"
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
    $Ui.RequestLabel.Text = $T.RequestLabel
    $Ui.PlaceholderText.Text = $T.Placeholder
    $Ui.AgentsTitle.Text = $T.AgentsTitle
    $Ui.AgentsBody.Text = $T.AgentsBody
    $Ui.ContinuationTitle.Text = $T.ContinuationTitle
    $Ui.ContinuationBody.Text = $T.ContinuationBody
    $Ui.CockpitTitle.Text = $T.CockpitTitle
    $Ui.CockpitBody.Text = $T.CockpitBody
    $Ui.ConfirmButton.Content = $T.Confirm
    $Ui.StatusText.Text = ""
}

$Ui.EnglishLanguage.Add_Checked({ Apply-Language })
$Ui.ChineseLanguage.Add_Checked({ Apply-Language })
$Ui.WorkRequest.Add_TextChanged({ Update-Placeholder })
$Ui.ConfirmButton.Add_Click({
    $Lang = Get-Language
    $Ui.StatusText.Text = $Copy[$Lang].Confirmed
})

Apply-Language
Update-Placeholder

if ($SmokeTest) {
    $Window.Close()
    "UI_SMOKE_OK"
    exit 0
}

$Window.ShowDialog() | Out-Null
