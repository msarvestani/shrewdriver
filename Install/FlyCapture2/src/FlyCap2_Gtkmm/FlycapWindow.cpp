//=============================================================================
// Copyright © 2017 FLIR Integrated Imaging Solutions, Inc. All Rights Reserved.
//
// This software is the confidential and proprietary information of FLIR
// Integrated Imaging Solutions, Inc. ("Confidential Information"). You
// shall not disclose such Confidential Information and shall use it only in
// accordance with the terms of the license agreement you entered into
// with FLIR Integrated Imaging Solutions, Inc. (FLIR).
//
// FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
// SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
// PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
// SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
// THIS SOFTWARE OR ITS DERIVATIVES.
//=============================================================================
//=============================================================================
// FlycapWindow.cpp,v 1.163 2010/08/20 21:18:28 soowei Exp
//=============================================================================

#include "Precompiled.h"
#include "FlycapWindow.h"
#include "SaveImageFileChooserDialog.h"
#include "HelpLauncher.h"
#include <string.h>

using namespace FlyCapture2;

int FlycapWindow::m_activeWindows = 0;

FlycapWindow::FlycapWindow() :
	m_processedFrameRate(60)
{
	m_pCamera = NULL;

	m_run = false;
	m_pNewImageEvent = NULL;
	m_pBusArrivalEvent = NULL;
	m_pBusRemovalEvent = NULL;
	m_pBusResetEvent = NULL;

	m_cameraPaused = false;
	m_prevPanePos = 260;

	m_imageWidth = 0;
	m_imageHeight = 0;
	m_bytesPerPixel = 0;
	m_receivedDataSize = 0;
	m_dataSize = 0;

	m_pInformationPane = NULL;
	m_pArea = NULL;
	m_pHistogramWindow = NULL;
	m_pEventStatisticsWindow = NULL;

	m_numEmitted = 0;

	m_saveImageLocation = "";
	m_saveImageFormat = PNG;

	m_previousSkippedImageCount = 0;
	m_previousLinkRecoveryCount = 0;
	m_previousTransmitFailureCount = 0;
	m_previousPacketResendRequested = 0;
	m_previousPacketResendReceived = 0;

	m_menuEnabled = true;
}

FlycapWindow::~FlycapWindow()
{
	if (m_pCamera != NULL)
	{
		delete m_pCamera;
		m_pCamera = NULL;
	}
}


	bool
FlycapWindow::Initialize()
{
	// Load Glade file

	const char* k_flycap2Glade = "FlyCap2_GTKmm.glade";

#ifdef GLIBMM_EXCEPTIONS_ENABLED
	try
	{
		m_refXml = Gnome::Glade::Xml::create(k_flycap2Glade);
	}
	catch(const Gnome::Glade::XmlError& ex)
	{
		char szSecondary[512];
		sprintf(
				szSecondary,
				"Error: %s. Make sure that the file is present.",
				ex.what().c_str() );

		Gtk::MessageDialog dialog( "Error loading Glade file", false, Gtk::MESSAGE_ERROR );
		dialog.set_secondary_text( szSecondary );
		dialog.run();

		return false;
	}
#else
	std::auto_ptr<Gnome::Glade::XmlError> error;
	m_refXml = Gnome::Glade::Xml::create(k_flycap2Glade, "", "", error);
	if(error.get())
	{
		char szSecondary[512];
		sprintf(
				szSecondary,
				"Error: %s. Make sure that the file is present.",
				ex.what().c_str() );

		Gtk::MessageDialog dialog( "Error loading Glade file", false, Gtk::MESSAGE_ERROR );
		dialog.set_secondary_text( szSecondary );
		dialog.run();

		return false;
	}
#endif

	m_refXml->get_widget( "window", m_pWindow );
	if ( m_pWindow == NULL )
	{
		return false;
	}

	GetWidgets();
	AttachSignals();

	LoadPGRLogo();
	LoadFlyCap2Icon();

	m_pWindow->set_default_icon( m_iconPixBuf );
	m_pWindow->set_default_size( 1024, 768 );
	m_pScrolledWindow->set_policy( Gtk::POLICY_AUTOMATIC, Gtk::POLICY_AUTOMATIC );

	m_pInformationPane->Initialize();

	UpdateColorProcessingMenu();

	m_pMenuDrawImage->set_active( true );
	m_pMenuShowToolbar->set_active( true );
	m_pMenuShowInfoPane->set_active( true );

	return true;
}

	void
FlycapWindow::GetWidgets()
{
	// Menu bar
	m_refXml->get_widget("menubar", m_pMenubar);

	// Tool bar
	m_refXml->get_widget("toolbar", m_pToolbar);

	// File menu
	m_refXml->get_widget("menu_new_camera", m_pMenuNewCamera);
	m_refXml->get_widget("menu_start", m_pMenuStart);
	m_refXml->get_widget("menu_stop", m_pMenuStop);
	m_refXml->get_widget("menu_pause", m_pMenuPause);
	m_refXml->get_widget("menu_save_as", m_pMenuSaveAs);
	m_refXml->get_widget("menu_quit", m_pMenuQuit);

	// View menu
	m_refXml->get_widget("menu_draw_image", m_pMenuDrawImage);
	m_refXml->get_widget("menu_draw_crosshair", m_pMenuDrawCrosshair);
	m_refXml->get_widget("menu_change_crosshair_color", m_pMenuChangeCrosshairColor);
	m_refXml->get_widget("menu_show_toolbar", m_pMenuShowToolbar);
	m_refXml->get_widget("menu_show_info_pane", m_pMenuShowInfoPane);
	m_refXml->get_widget("menu_stretch_image", m_pMenuStretchImage);
	m_refXml->get_widget("menu_fullscreen", m_pMenuFullscreen);

	// Color processing menu
	m_refXml->get_widget("menu_cpa_none", m_pMenuCPA_None);
	m_refXml->get_widget("menu_cpa_nnf", m_pMenuCPA_NNF);
	m_refXml->get_widget("menu_cpa_hq_linear", m_pMenuCPA_HQ_Linear);
	m_refXml->get_widget("menu_cpa_edge_sensing", m_pMenuCPA_Edge_Sensing);
	m_refXml->get_widget("menu_cpa_df", m_pMenuCPA_DirectionalFilter);
	m_refXml->get_widget("menu_cpa_rigorous", m_pMenuCPA_Rigorous);
	m_refXml->get_widget("menu_cpa_ipp", m_pMenuCPA_IPP);

	// Help menu
	m_refXml->get_widget("menu_help", m_pMenuHelp);
	m_refXml->get_widget("menu_about", m_pMenuAbout);

	// Tool bar buttons
	m_refXml->get_widget("toolbutton_item_new_camera", m_pNewCameraButton);
	m_refXml->get_widget("toolbar_item_start", m_pStartButton);
	m_refXml->get_widget("toolbar_item_pause", m_pPauseButton);
	m_refXml->get_widget("toolbar_item_stop", m_pStopButton);
	m_refXml->get_widget("toolbar_item_save_image", m_pSaveImageButton);
	m_refXml->get_widget("toolbar_item_cam_ctl", m_pCamCtlButton);
	m_refXml->get_widget("toolbar_item_histogram", m_pHistogramButton);
	m_refXml->get_widget("toolbar_item_event_statistics", m_pEventStatisticsButton);

	// The scrolled window that holds the drawing area
	m_refXml->get_widget("scrolledwindow1", m_pScrolledWindow);

	// Status bar
	m_refXml->get_widget("statusbarRGB", m_pStatusBarRGB);

	// Scrollbars
	m_refXml->get_widget("disp_image_hscrollbar", m_pHScrollbar);
	m_refXml->get_widget("disp_image_vscrollbar", m_pVScrollbar);

	// Pane that holds the scrolled window and info pane
	m_refXml->get_widget_derived("hpaned", m_pInformationPane);

	// Custom drawing area
	m_refXml->get_widget_derived("disp_image", m_pArea);

	// Histogram window
	m_refXml->get_widget_derived("window_histogram", m_pHistogramWindow);

	// Event statistics window
	m_refXml->get_widget_derived("window_events", m_pEventStatisticsWindow);
}

	void
FlycapWindow::AttachSignals()
{
	m_pWindow->signal_delete_event().connect(sigc::mem_fun( *this, &FlycapWindow::OnDestroy ));
	m_pWindow->signal_scroll_event().connect(sigc::mem_fun( *this, &FlycapWindow::OnMouseScroll ));

	m_pMenuNewCamera->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnToolbarNewCamera ));
	m_pMenuStart->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnToolbarStart ));
	m_menuPauseConnection = m_pMenuPause->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuPaused));
	m_pMenuStop->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnToolbarStop ));
	m_pMenuSaveAs->signal_activate().connect(sigc::mem_fun(*this, &FlycapWindow::OnMenuSaveAs ));
	m_pMenuQuit->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuQuit ));

	m_pMenuDrawCrosshair->signal_toggled().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuDrawCrosshair ));
	m_pMenuChangeCrosshairColor->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuChangeCrosshairColor ));
	m_pMenuShowToolbar->signal_toggled().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuShowToolbar ));
	m_pMenuShowInfoPane->signal_toggled().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuShowInfoPane ));
	m_pMenuStretchImage->signal_toggled().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuStretchImage ));
	m_pMenuFullscreen->signal_toggled().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuFullscreen ));

	m_pMenuCPA_None->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				NO_COLOR_PROCESSING,
				m_pMenuCPA_None ) );

	m_pMenuCPA_NNF->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				NEAREST_NEIGHBOR,
				m_pMenuCPA_NNF ) );

	m_pMenuCPA_HQ_Linear->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				HQ_LINEAR,
				m_pMenuCPA_HQ_Linear ) );

	m_pMenuCPA_Edge_Sensing->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				EDGE_SENSING,
				m_pMenuCPA_Edge_Sensing ) );

	m_pMenuCPA_DirectionalFilter->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				DIRECTIONAL_FILTER,
				m_pMenuCPA_DirectionalFilter ) );

	m_pMenuCPA_Rigorous->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				RIGOROUS,
				m_pMenuCPA_Rigorous ) );

	m_pMenuCPA_IPP->signal_toggled().connect(
			sigc::bind<ColorProcessingAlgorithm, Gtk::RadioMenuItem*>(
				sigc::mem_fun(*this, &FlycapWindow::OnMenuCPAClicked),
				IPP,
				m_pMenuCPA_IPP ) );

	m_pMenuHelp->signal_activate().connect(sigc::mem_fun(*this, &FlycapWindow::OnMenuHelp));
	m_pMenuAbout->signal_activate().connect(sigc::mem_fun( *this, &FlycapWindow::OnMenuAbout));

	m_pNewCameraButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarNewCamera));
	m_pStartButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarStart));
	m_toolbarPauseConnection = m_pPauseButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarPaused));
	m_pStopButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarStop));
	m_pSaveImageButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnMenuSaveAs));
	m_pCamCtlButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarCameraControl));
	m_pHistogramButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarHistogram));
	m_pEventStatisticsButton->signal_clicked().connect(sigc::mem_fun(*this, &FlycapWindow::OnToolbarEventStatistics));

	m_pHScrollbar->signal_change_value().connect(sigc::mem_fun(*this, &FlycapWindow::OnHScroll));
	m_pVScrollbar->signal_change_value().connect(sigc::mem_fun(*this, &FlycapWindow::OnVScroll));

	m_pArea->signal_offset_changed().connect(sigc::mem_fun(*this, &FlycapWindow::OnImageMoved));

	m_pNewImageEvent = new Glib::Dispatcher();
	m_pNewImageEvent->connect(sigc::mem_fun( *this, &FlycapWindow::OnImageCaptured ));

	m_pBusArrivalEvent = new Glib::Dispatcher();
	m_pBusArrivalEvent->connect(sigc::mem_fun( *this, &FlycapWindow::OnBusArrivalHandler ));

	m_pBusRemovalEvent = new Glib::Dispatcher();
	m_pBusRemovalEvent->connect(sigc::mem_fun( *this, &FlycapWindow::OnBusRemovalHandler ));

	m_pBusResetEvent = new Glib::Dispatcher();
	m_pBusResetEvent->connect(sigc::mem_fun( *this, &FlycapWindow::OnBusResetHandler ));

	m_pHScrollbar->set_range( 0, 1.0);
	m_pHScrollbar->set_increments( 0.01, 0.1 );

	m_pVScrollbar->set_range( 0, 1.0);
	m_pVScrollbar->set_increments( 0.01, 0.1 );
}

	bool
FlycapWindow::Cleanup()
{
	if (m_pNewImageEvent != NULL)
	{
		delete m_pNewImageEvent;
		m_pNewImageEvent = NULL;
	}

	if (m_pBusArrivalEvent != NULL)
	{
		delete m_pBusArrivalEvent;
		m_pBusArrivalEvent = NULL;
	}

	if (m_pBusRemovalEvent != NULL)
	{
		delete m_pBusRemovalEvent;
		m_pBusRemovalEvent = NULL;
	}

	if (m_pBusResetEvent != NULL)
	{
		delete m_pBusResetEvent;
		m_pBusResetEvent = NULL;
	}

	return true;
}

	bool
FlycapWindow::OnDestroy( GdkEventAny* /*event*/ )
{
	// The destroy signal is emitted when the "X" button is clicked

	// Stop the camera and the grab thread
	Stop();

	if ( --m_activeWindows <= 0 )
	{
		// If there are no more windows left open, quit the main thread
		Gtk::Main::quit();
	}
	else
	{
		// Hide the window
		m_pWindow->hide();
	}

	return true;
}

	void
FlycapWindow::OnMenuSaveAs()
{
	Glib::Mutex::Lock saveLock(m_rawImageMutex);

	// Make a local copy of the image
	Image tempImage;
	tempImage.DeepCopy( &m_rawImage );

	saveLock.release();

	time_t rawtime;
	struct tm * timeinfo;
	time( &rawtime );
	timeinfo = localtime( &rawtime );

	char timestamp[64];
	strftime( timestamp, 64, "%Y-%m-%d-%H%M%S", timeinfo );

	char tempFilename[128];
	sprintf( tempFilename, "%u-%s", m_camInfo.serialNumber, timestamp );

	std::string defaultFileName( tempFilename );

	SaveImageFileChooserDialog saveDialog( m_pWindow, defaultFileName, m_saveImageFormat, m_saveImageLocation );

	std::string filename;
	saveDialog.Run( filename, m_saveImageFormat, m_saveImageLocation );
	if ( filename.length() == 0 )
	{
		return;
	}

	Error rawError;
	if ( m_saveImageFormat == RAW )
	{
		rawError = tempImage.Save( filename.c_str(), RAW );
		if ( rawError != PGRERROR_OK )
		{
			ShowErrorMessageDialog( "Failed to save image", rawError );
		}
	}
	else if ( m_saveImageFormat == PGM )
	{
		PixelFormat tempPixelFormat = tempImage.GetPixelFormat();
		if (tempPixelFormat == PIXEL_FORMAT_MONO8 ||
				tempPixelFormat == PIXEL_FORMAT_MONO12 ||
				tempPixelFormat == PIXEL_FORMAT_MONO16 ||
				tempPixelFormat == PIXEL_FORMAT_RAW8 ||
				tempPixelFormat == PIXEL_FORMAT_RAW12 ||
				tempPixelFormat == PIXEL_FORMAT_RAW16)
		{
			Error error = tempImage.Save( filename.c_str(), m_saveImageFormat );
			if ( error != PGRERROR_OK )
			{
				ShowErrorMessageDialog( "Failed to convert image", error );
			}
		}
		else
		{
			ShowErrorMessageDialog( "Invalid file format", "Non mono / raw images cannot be saved as PGM." );
		}
	}
	else
	{
		Error conversionError;
		Image convertedImage;
		conversionError = tempImage.Convert( &convertedImage );
		if ( conversionError != PGRERROR_OK )
		{
			ShowErrorMessageDialog( "Failed to convert image", conversionError );
		}

		Error convertedError;
		convertedError = convertedImage.Save( filename.c_str(), m_saveImageFormat );
		if ( convertedError != PGRERROR_OK )
		{
			ShowErrorMessageDialog( "Failed to save image", convertedError );
		}
	}
}

	bool
FlycapWindow::OnMouseScroll( GdkEventScroll* event )
{
	if ( event->direction == GDK_SCROLL_DOWN)
	{
		m_pArea->ZoomIn();
	}
	else if ( event->direction == GDK_SCROLL_UP)
	{
		m_pArea->ZoomOut();
	}

	return true;
}

	void
FlycapWindow::OnMenuQuit()
{
	Stop();

	Gtk::Main::quit();
	return;
}

	void
FlycapWindow::OnToolbarNewCamera()
{
	bool retVal = Stop();

	m_camCtlDlg.Hide();
	m_camCtlDlg.Disconnect();

	m_pCamera->Disconnect();

	m_pHistogramWindow->hide();
	m_pHistogramWindow->Reset();

	m_pEventStatisticsWindow->hide();
	m_pEventStatisticsWindow->Reset();

	// Reset event statistic
	m_previousSkippedImageCount = 0;
	m_previousLinkRecoveryCount = 0;
	m_previousTransmitFailureCount = 0;

	// Reset pause buttons
	m_pPauseButton->set_active ( false );
	m_pMenuPause->set_active( false );
	m_pPauseButton->set_sensitive();
	m_pMenuPause->set_sensitive();
	m_cameraPaused = false;

	// Disable the toolbar
	m_pToolbar->set_sensitive( false );

	// Display the camera selection dialog
	CameraSelectionDlg camSlnDlg;
	PGRGuid arGuid[64];
	unsigned int size = 64;

	// Hide main window
	m_pWindow->hide();

	bool ok;
	camSlnDlg.ShowModal( &ok, arGuid, &size );

	// Enable the toolbar
	m_pToolbar->set_sensitive( true );

	if ( ok != true )
	{
		// Cancel selected
		OnMenuQuit();

		return;
	}

	if ( size < 1 )
	{
		// Inform user that they can only choose 1 camera
		Gtk::MessageDialog dialog( "No cameras selected", false, Gtk::MESSAGE_ERROR );
		dialog.set_secondary_text( "There were no cameras selected." );
		dialog.run();

		return;
	}
	else if ( size > 1 )
	{
		// Inform user that they can only choose 1 camera
		Gtk::MessageDialog dialog( "Unable to start more than 1 camera", false, Gtk::MESSAGE_ERROR );
		dialog.set_secondary_text( "Unable to start more than 1 camera in this mode." );
		dialog.run();

		return;
	}

	retVal = Start( arGuid[0] );
}

	void
FlycapWindow::OnToolbarStart()
{
	if ( m_pCamera->IsConnected() != true )
	{
		OnToolbarNewCamera();
		return;
	}

	Error error;
	error = m_pCamera->StartCapture();
	if ( error == PGRERROR_ISOCH_BANDWIDTH_EXCEEDED )
	{
		ShowErrorMessageDialog( "Bandwidth exceeded", error );
		return;
	}
	else if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to start image capture", error, true );
		return;
	}

	m_cameraPaused = false;

	ResetPauseButtons(true);

	m_pSaveImageButton->set_sensitive(true);
	m_pMenuSaveAs->set_sensitive( true );
	m_pStartButton->set_sensitive( false );
	m_pStopButton->set_sensitive( true );

	m_pMenuStart->set_sensitive( false );
	m_pMenuStop->set_sensitive( true );

	RegisterCallbacks();

	LaunchGrabThread();
}

void FlycapWindow::OnToolbarPaused()
{
	if(!m_cameraPaused)
	{
		// Pause camera
		if ( m_pCamera->IsConnected() != true )
		{
			return;
		}

		// error is not checked as sometime camera
		// could be started correctly but error was
		// returned
		Error error = m_pCamera->StopCapture();

		m_cameraPaused = true;

		// Sync menu button with toolbar item
		m_menuPauseConnection.block();
		m_pMenuPause->set_active();
		m_menuPauseConnection.block(false);
	}
	else
	{
		// Un-pause camera
		if ( m_pCamera->IsConnected() != true )
		{
			return;
		}

		// error is not checked as sometime camera
		// could be started correctly but error was
		// returned
		Error error = m_pCamera->StartCapture();

		m_cameraPaused = false;

		// Sync menu button with toolbar item
		m_menuPauseConnection.block();
		m_pMenuPause->set_active( false );
		m_menuPauseConnection.block(false);
	}
}

void FlycapWindow::OnMenuPaused()
{
	if(!m_cameraPaused)
	{
		// Pause camera
		if ( m_pCamera->IsConnected() != true )
		{
			return;
		}

		Error error = m_pCamera->StopCapture();

		m_cameraPaused = true;

		// Sync toolbar button with menu item
		m_toolbarPauseConnection.block();
		m_pPauseButton->set_active();
		m_toolbarPauseConnection.block(false);
	}
	else
	{
		// Un-pause camera
		if ( m_pCamera->IsConnected() != true )
		{
			return;
		}

		Error error = m_pCamera->StartCapture();

		m_cameraPaused = false;

		// Sync toolbar button with menu item
		m_toolbarPauseConnection.block();
		m_pPauseButton->set_active(false);
		m_toolbarPauseConnection.block(false);
		m_pPauseButton->set_active ( false );
	}
}

	void
FlycapWindow::OnToolbarStop()
{
	ResetPauseButtons(false);
	Stop();
}

	void
FlycapWindow::ResetPauseButtons(bool sensitivity)
{
	m_cameraPaused = false;
	m_menuPauseConnection.block();
	m_pMenuPause->set_active( false );
	m_menuPauseConnection.block(false);
	m_toolbarPauseConnection.block();
	m_pPauseButton->set_active(false);
	m_toolbarPauseConnection.block(false);
	m_pPauseButton->set_sensitive( sensitivity );
	m_pMenuPause->set_sensitive( sensitivity );
}

	void
FlycapWindow::OnToolbarCameraControl()
{
	m_camCtlDlg.IsVisible() ? m_camCtlDlg.Hide() : m_camCtlDlg.Show();
}

	void
FlycapWindow::OnToolbarHistogram()
{
	m_pHistogramWindow->is_visible() ? m_pHistogramWindow->hide() : m_pHistogramWindow->show();
}

void FlycapWindow::OnToolbarEventStatistics()
{
	m_pEventStatisticsWindow->is_visible() ? m_pEventStatisticsWindow->hide() : m_pEventStatisticsWindow->show();
}

	bool
FlycapWindow::Start( PGRGuid guid )
{
	Error error;

	if ( m_pCamera != NULL )
	{
		delete m_pCamera;
		m_pCamera = NULL;
	}

	InterfaceType ifType;
	error = m_busMgr.GetInterfaceTypeFromGuid( &guid, &ifType );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to get interface for camera", error );
		return false;
	}

	if ( ifType == INTERFACE_GIGE )
	{
		m_pCamera = new GigECamera;
	}
	else
	{
		m_pCamera = new Camera;
	}

	error = m_pCamera->Connect( &guid );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to connect to camera", error );
		return false;
	}

	// Force the camera to PGR's Y16 endianness
	ForcePGRY16Mode();

	// Connect the camera control dialog to the selected camera
	m_camCtlDlg.Connect( m_pCamera );

	// Get the camera info and print it out
	error = m_pCamera->GetCameraInfo( &m_camInfo );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to get camera info from camera", error );
		return false;
	}

	FC2Version version;
	Utilities::GetLibraryVersion( &version );

	char title[512];
	sprintf(
			title,
			"FlyCap2 %u.%u.%u.%u - %s %s (%u)",
			version.major,
			version.minor,
			version.type,
			version.build,
			m_camInfo.vendorName,
			m_camInfo.modelName,
			m_camInfo.serialNumber );
	m_pWindow->set_title( title );

	error = m_pCamera->StartCapture();
	if ( error == PGRERROR_ISOCH_BANDWIDTH_EXCEEDED )
	{
		ShowErrorMessageDialog( "Bandwidth exceeded", error );
		m_camCtlDlg.Disconnect();
		delete m_pCamera;
		m_pCamera = NULL;
		return false;
	}
	else if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to start image capture", error, true );
		m_camCtlDlg.Disconnect();
		delete m_pCamera;
		m_pCamera = NULL;
		return false;
	}

	// Reset frame rate counters
	m_processedFrameRate.Reset();
	m_pArea->ResetFrameRate();

	RegisterCallbacks();

	SetRunStatus( true );

	LaunchGrabThread();

	m_pSaveImageButton->set_sensitive(true);

	m_pStartButton->set_sensitive( false );
	m_pStopButton->set_sensitive( true );

	m_pMenuStart->set_sensitive( false );
	m_pMenuStop->set_sensitive( true );

	m_pCamCtlButton->set_sensitive(true);
	m_pHistogramButton->set_sensitive(true);
	m_pEventStatisticsButton->set_sensitive(true);

	m_pMenuSaveAs->set_sensitive( true );

	// Show window
	m_pWindow->show();

	return true;
}


	bool
FlycapWindow::Stop()
{
	if( GetRunStatus() != true )
	{
		return false;
	}

	// Stop the image capture
	Error error;
	error = m_pCamera->StopCapture();
	if ( error != PGRERROR_OK )
	{
		// This may fail when the camera was removed, so don't show
		// an error message
	}

	KillGrabThread();

	UnregisterCallbacks();

	// Stop stretching and fullscreen
	//m_pMenuStretchImage->set_active( false );
	m_pMenuFullscreen->set_active( false );

	// Load the PGR logo file
	LoadPGRLogo();

	// Assign the new pix buf to the drawing area and redraw it
	m_pArea->queue_draw();

	// Hide the camera control dialog
	m_camCtlDlg.Hide();

	// Hide the histogram window
	m_pHistogramWindow->hide();

	// Hide the event statistics window
	m_pEventStatisticsWindow->hide();

	// Update the status bar
	UpdateStatusBar();

	m_pSaveImageButton->set_sensitive(false);

	m_pStartButton->set_sensitive( true );
	m_pStopButton->set_sensitive( false );

	m_pMenuStart->set_sensitive( true );
	m_pMenuStop->set_sensitive( false );

	m_pMenuSaveAs->set_sensitive( false );

	return true;
}

	void
FlycapWindow::RegisterCallbacks()
{
	Error error;

	// Register arrival callback
	error = m_busMgr.RegisterCallback( &FlycapWindow::OnBusArrival, ARRIVAL, this, &m_cbArrivalHandle );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to register bus arrival callback", error );
	}

	// Register removal callback
	error = m_busMgr.RegisterCallback( &FlycapWindow::OnBusRemoval, REMOVAL, this, &m_cbRemovalHandle );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to register bus removal callback", error );
	}

	// Register reset callback
	error = m_busMgr.RegisterCallback( &FlycapWindow::OnBusReset, BUS_RESET, this, &m_cbResetHandle );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to register bus reset callback", error );
	}
}

	void
FlycapWindow::UnregisterCallbacks()
{
	Error error;

	// Unregister arrival callback
	error = m_busMgr.UnregisterCallback( m_cbArrivalHandle );
	if ( error != PGRERROR_OK )
	{
		//ShowErrorMessageDialog( "Failed to unregister callback", error );
	}

	// Unregister removal callback
	error = m_busMgr.UnregisterCallback( m_cbRemovalHandle );
	if ( error != PGRERROR_OK )
	{
		//ShowErrorMessageDialog( "Failed to unregister callback", error );
	}

	// Unregister removal callback
	error = m_busMgr.UnregisterCallback( m_cbResetHandle );
	if ( error != PGRERROR_OK )
	{
		//ShowErrorMessageDialog( "Failed to unregister callback", error );
	}
}

	void
FlycapWindow::LaunchGrabThread()
{
	SetRunStatus( true );

	m_pGrabLoop = Glib::Thread::create(
			sigc::mem_fun(*this, &FlycapWindow::GrabLoop),
			true );
}

	void
FlycapWindow::KillGrabThread()
{
	// Kill the grab thread
	SetRunStatus( false );
	m_pGrabLoop->join();
}

	void
FlycapWindow::SetRunStatus( bool runStatus )
{
	Glib::Mutex::Lock saveLock(m_runMutex);
	m_run = runStatus;
}

	bool
FlycapWindow::GetRunStatus()
{
	Glib::Mutex::Lock saveLock(m_runMutex);
	return m_run;
}

	void
FlycapWindow::GrabLoop()
{
	while( GetRunStatus() == true )
	{
		if(!m_cameraPaused)
		{
			// Get the image
			Image tempImage;
			Error error = m_pCamera->RetrieveBuffer( &tempImage );
			if ( error != PGRERROR_OK )
			{
				if (error == PGRERROR_IMAGE_CONSISTENCY_ERROR)
				{
					m_pEventStatisticsWindow->AddEvent(IMAGE_CONSISTENCY_ERRORS);
					PrintGrabLoopError( error );
					continue;
				}
				else if(error == PGRERROR_TIMEOUT)
				{
					PrintGrabLoopError( error );
					continue;
				}
				else
				{
					PrintGrabLoopError( error );
					//SetRunStatus(false);
					continue;
				}
			}

			{
				// Update color-processing algorithm menu based on pixel format
				if(!IsRAWPixelFormat(tempImage))
				{
					// Disable color-processing menu
					if(m_menuEnabled)
					{
						ToggleColorMenu(false);
						m_menuEnabled = false;
					}
				}
				else
				{
					// Enable color-processing menu for RAW pixel formats
					if(!m_menuEnabled)
					{
						ToggleColorMenu(true);
						m_menuEnabled = true;
					}
				}
			}

			{
				Glib::Mutex::Lock saveLock(m_rawImageMutex);
				m_rawImage = tempImage;
				m_imageWidth = m_rawImage.GetCols();
				m_imageHeight = m_rawImage.GetRows();
				m_receivedDataSize = m_rawImage.GetReceivedDataSize();
				m_dataSize = m_rawImage.GetDataSize();
				m_bytesPerPixel = m_rawImage.GetBitsPerPixel() / 8.0f;
			}

			// A new image was received
			m_processedFrameRate.NewFrame();

			m_pEventStatisticsWindow->AddEvent(TOTAL_NUMBER_OF_FRAMES);


			// Get the image dimensions
			PixelFormat pixelFormat;
			BayerTileFormat bayerFormat;
			unsigned int rows, cols, stride;
			m_rawImage.GetDimensions( &rows, &cols, &stride, &pixelFormat, &bayerFormat );

			// Try to lock the window's pixbuf.
			Glib::Mutex::Lock rawImageLock(m_rawImageMutex, Glib::NOT_LOCK );
			if ( rawImageLock.try_acquire() )
			{
				m_pHistogramWindow->SetImageForStatistics( m_rawImage );

				rawImageLock.release();

				Glib::Mutex::Lock emitLock( m_emitMutex );

				m_pNewImageEvent->emit();
				m_numEmitted++;

				emitLock.release();
			}
		}
		else
		{
			Glib::Mutex::Lock emitLock( m_emitMutex );

			m_pNewImageEvent->emit();
			m_numEmitted++;

			emitLock.release();

			// Prevent loop from running too fast when camera is paused
			Glib::usleep(100000);
		}
	}
}

void FlycapWindow::ToggleColorMenu(bool enable)
{

	m_pMenuCPA_None->set_sensitive(enable);
	m_pMenuCPA_NNF->set_sensitive(enable);
	m_pMenuCPA_HQ_Linear->set_sensitive(enable);
	m_pMenuCPA_Edge_Sensing->set_sensitive(enable);
	m_pMenuCPA_DirectionalFilter->set_sensitive(enable);
	m_pMenuCPA_Rigorous->set_sensitive(enable);
	m_pMenuCPA_IPP->set_sensitive(enable);
}

bool FlycapWindow::IsRAWPixelFormat(Image &image)
{
	if(image.GetPixelFormat() == PIXEL_FORMAT_RAW8 || image.GetPixelFormat() == PIXEL_FORMAT_RAW12 ||image.GetPixelFormat() == PIXEL_FORMAT_RAW16)
	{
		return true;
	}
	else
	{
		return false;
	}
}

	void
FlycapWindow::PrintGrabLoopError( Error fc2Error )
{
	time_t rawtime;
	struct tm * timeinfo;
	time( &rawtime );
	timeinfo = localtime( &rawtime );

	char currTimeStr[128];
	sprintf( currTimeStr, "%s", asctime( timeinfo ) );
	currTimeStr[ strlen(currTimeStr) - 1 ] = '\0';

	char errorMsg[1024];
	sprintf(
			errorMsg,
			"%s: Grab loop had an error: %s\n",
			currTimeStr,
			fc2Error.GetDescription() );

	std::cout << errorMsg;
}

	void
FlycapWindow::OnImageCaptured()
{
	// This means that an image was grabbed (and possibly converted) in the
	// grab loop

	Glib::Mutex::Lock emitLock( m_emitMutex );

	if ( m_numEmitted == 0 )
	{
		return;
	}
	else
	{
		m_numEmitted = 0;
	}

	emitLock.release();

	Glib::Mutex::Lock imageLock(m_rawImageMutex, Glib::NOT_LOCK );
	if ( imageLock.try_acquire() == true )
	{
		if( m_pMenuDrawImage->get_active() == true )
		{
			m_pArea->SetImage(&m_rawImage);

			// Redraw the image
			m_pArea->queue_draw();
		}

		UpdateInformationPane();
		UpdateStatusBar();
		UpdateHistogramWindow();
		UpdateEventStatisticsWindow();
	}
}

	bool
FlycapWindow::Run( PGRGuid guid )
{
	bool retVal;

	retVal = Initialize();
	if ( retVal != true )
	{
		return false;
	}

	retVal = Start( guid );
	if ( retVal != true )
	{
		return false;
	}

	m_pWindow->show();
	m_pArea->show();

	m_activeWindows++;

	return true;
}

	void
FlycapWindow::SetTimestamping( bool onOff )
{
	Error error;
	EmbeddedImageInfo info;

	// Get configuration
	error = m_pCamera->GetEmbeddedImageInfo( &info );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to get embedded image info", error );
		return;
	}

	// Set timestamping to on
	if ( onOff == true )
	{
		info.timestamp.onOff = true;
	}
	else
	{
		info.timestamp.onOff = false;
	}

	// Set configuration
	error = m_pCamera->SetEmbeddedImageInfo( &info );
	if ( error != PGRERROR_OK )
	{
		ShowErrorMessageDialog( "Failed to set embededded image info", error );
		return;
	}
}

	void
FlycapWindow::ForcePGRY16Mode()
{
	Error error;
	const unsigned int k_imageDataFmtReg = 0x1048;
	unsigned int value = 0;
	error = m_pCamera->ReadRegister( k_imageDataFmtReg, &value );
	if ( error != PGRERROR_OK )
	{
		// Error
	}

	value &= ~(0x1 << 0);

	error = m_pCamera->WriteRegister( k_imageDataFmtReg, value );
	if ( error != PGRERROR_OK )
	{
		// Error
	}
}

	void
FlycapWindow::UpdateColorProcessingMenu()
{
	ColorProcessingAlgorithm cpa = Image::GetDefaultColorProcessing();

	switch (cpa)
	{
		case NO_COLOR_PROCESSING:
			m_pMenuCPA_None->set_active( true );
			break;

		case NEAREST_NEIGHBOR:
			m_pMenuCPA_NNF->set_active( true );
			break;

		case HQ_LINEAR:
			m_pMenuCPA_HQ_Linear->set_active( true );
			break;

		case EDGE_SENSING:
			m_pMenuCPA_Edge_Sensing->set_active( true );
			break;

		case DIRECTIONAL_FILTER:
			m_pMenuCPA_DirectionalFilter->set_active( true );
			break;

		case RIGOROUS:
			m_pMenuCPA_Rigorous->set_active( true );
			break;

		case IPP:
			m_pMenuCPA_IPP->set_active( true );
			break;

		case DEFAULT:
		default:
			break;
	}
}

void FlycapWindow::ParseTimeRegister(
		unsigned int timeRegVal,
		unsigned int& hours,
		unsigned int& mins,
		unsigned int& seconds )
{
	hours = timeRegVal / (60 * 60);
	mins = (timeRegVal - (hours * 60 * 60)) / 60;
	seconds = timeRegVal - (hours * 60 * 60) - (mins * 60);
}

	void
FlycapWindow::UpdateInformationPane()
{
	Error error;
	InformationPane::InformationPaneStruct infoStruct;

	// Set up the frame rate data
	Property prop;
	prop.type = FRAME_RATE;
	error = m_pCamera->GetProperty( &prop );

	infoStruct.fps.requestedFrameRate = (error == PGRERROR_OK) ? prop.absValue : 0.0;
	infoStruct.fps.processedFrameRate = m_processedFrameRate.GetFrameRate();
	if( m_pMenuDrawImage->get_active() == true && !m_cameraPaused )
	{
		infoStruct.fps.displayedFrameRate = m_pArea->GetDisplayedFrameRate();
	}
	else
	{
		infoStruct.fps.displayedFrameRate = 0.0;
	}

	// Set up the timestamp data
	infoStruct.timestamp = m_rawImage.GetTimeStamp();

	// Set up the image info data
	m_rawImage.GetDimensions(
			&infoStruct.imageInfo.height,
			&infoStruct.imageInfo.width,
			&infoStruct.imageInfo.stride,
			&infoStruct.imageInfo.pixFmt );

	// Set up the embedded image info data
	const unsigned int k_frameInfoReg = 0x12F8;
	unsigned int frameInfoRegVal = 0;
	error = m_pCamera->ReadRegister( k_frameInfoReg, &frameInfoRegVal );
	if ( error == PGRERROR_OK && (frameInfoRegVal >> 31) != 0 )
	{
		const int k_numEmbeddedInfo = 10;

		ImageMetadata metadata = m_rawImage.GetMetadata();
		unsigned int* pEmbeddedInfo = infoStruct.embeddedInfo.arEmbeddedInfo;

		for (int i=0; i < k_numEmbeddedInfo; i++)
		{
			switch (i)
			{
				case 0: pEmbeddedInfo[i] = metadata.embeddedTimeStamp; break;
				case 1: pEmbeddedInfo[i] = metadata.embeddedGain; break;
				case 2: pEmbeddedInfo[i] = metadata.embeddedShutter; break;
				case 3: pEmbeddedInfo[i] = metadata.embeddedBrightness; break;
				case 4: pEmbeddedInfo[i] = metadata.embeddedExposure; break;
				case 5: pEmbeddedInfo[i] = metadata.embeddedWhiteBalance; break;
				case 6: pEmbeddedInfo[i] = metadata.embeddedFrameCounter; break;
				case 7: pEmbeddedInfo[i] = metadata.embeddedStrobePattern; break;
				case 8: pEmbeddedInfo[i] = metadata.embeddedGPIOPinState; break;
				case 9: pEmbeddedInfo[i] = metadata.embeddedROIPosition; break;
			}
		}
	}

	// Set up the diagnostics info
	const unsigned int k_frameSkippedReg = 0x12C0;
	unsigned int frameSkippedRegVal = 0;
	error = m_pCamera->ReadRegister( k_frameSkippedReg, &frameSkippedRegVal );
	if (error != PGRERROR_OK  ||
			m_camInfo.interfaceType != INTERFACE_USB3 ||
			m_camInfo.iidcVer < 132 ||
			( m_camInfo.iidcVer >= 132 && (frameSkippedRegVal & 0x80000000) == 0))
	{
		infoStruct.diagnostics.skippedFrames = -1;
	}
	else
	{
		const unsigned int skippedFrames = frameSkippedRegVal & 0x7FFFFFFF;
		infoStruct.diagnostics.skippedFrames = skippedFrames;
		if (skippedFrames != m_previousSkippedImageCount)
		{
			const unsigned int numNewEvents = skippedFrames - m_previousSkippedImageCount;
			for (unsigned int i=0; i < numNewEvents; i++)
			{
				m_pEventStatisticsWindow->AddEvent(SKIPPED_IMAGES);
			}
			m_previousSkippedImageCount = skippedFrames;
		}
	}

	const unsigned int k_linkRecoveryCountReg = 0x12C4;
	unsigned int linkRecoveryCountRegVal = 0;
	error = m_pCamera->ReadRegister( k_linkRecoveryCountReg, &linkRecoveryCountRegVal );
	if (error != PGRERROR_OK  ||
			m_camInfo.interfaceType != INTERFACE_USB3 ||
			m_camInfo.iidcVer < 132 ||
			(m_camInfo.iidcVer >= 132 && (linkRecoveryCountRegVal & 0x80000000) == 0))
	{
		infoStruct.diagnostics.linkRecoveryCount = -1;
	}
	else
	{
		const unsigned int linkRecoveryCount = linkRecoveryCountRegVal & 0x7FFFFFFF;
		infoStruct.diagnostics.linkRecoveryCount = linkRecoveryCount;
		if (linkRecoveryCount != m_previousLinkRecoveryCount)
		{
			const unsigned int numNewEvents = linkRecoveryCount - m_previousLinkRecoveryCount;
			for (unsigned int i=0; i < numNewEvents; i++)
			{
				m_pEventStatisticsWindow->AddEvent(RECOVERY_COUNT);
			}
			m_previousLinkRecoveryCount = linkRecoveryCount;
		}
	}

	const unsigned int k_transmitFailureReg = 0x12FC;
	unsigned int transmitFailureRegVal = 0;
	error = m_pCamera->ReadRegister( k_transmitFailureReg, &transmitFailureRegVal );
	if (error != PGRERROR_OK  ||
			(m_camInfo.iidcVer >= 132 && (transmitFailureRegVal & 0x80000000) == 0))
	{
		infoStruct.diagnostics.transmitFailures = -1;
	}
	else
	{
		const unsigned int transmitFailureCount = transmitFailureRegVal & 0x7FFFFFFF;
		infoStruct.diagnostics.transmitFailures = transmitFailureCount;
		if (transmitFailureCount != m_previousTransmitFailureCount)
		{
			const unsigned int numNewEvents = transmitFailureCount - m_previousTransmitFailureCount;
			for (unsigned int i=0; i < numNewEvents; i++)
			{
				m_pEventStatisticsWindow->AddEvent(TRANSMIT_FAILURES);
			}
			m_previousTransmitFailureCount = transmitFailureCount;
		}
	}

	const unsigned int k_initializeTimeReg = 0x12E0;
	unsigned int initializeTimeRegVal = 0;
	error = m_pCamera->ReadRegister( k_initializeTimeReg, &initializeTimeRegVal );
	if ( error != PGRERROR_OK )
	{
		infoStruct.diagnostics.timeSinceInitialization = "";
	}
	else
	{
		unsigned int numHours = 0;
		unsigned int numMins = 0;
		unsigned int numSeconds = 0;

		ParseTimeRegister( initializeTimeRegVal, numHours, numMins, numSeconds );

		char timeStr[512];
		sprintf(
				timeStr,
				"%uh %um %us",
				numHours,
				numMins,
				numSeconds );

		infoStruct.diagnostics.timeSinceInitialization = timeStr;
	}

	const unsigned int k_busResetTimeReg = 0x12E4;
	unsigned int busResetTimeRegVal = 0;
	error = m_pCamera->ReadRegister( k_busResetTimeReg, &busResetTimeRegVal );
	if ( error != PGRERROR_OK )
	{
		infoStruct.diagnostics.timeSinceLastBusReset = "";
	}
	else
	{
		unsigned int numHours = 0;
		unsigned int numMins = 0;
		unsigned int numSeconds = 0;

		ParseTimeRegister( busResetTimeRegVal, numHours, numMins, numSeconds );

		char timeStr[512];
		sprintf(
				timeStr,
				"%uh %um %us",
				numHours,
				numMins,
				numSeconds );

		infoStruct.diagnostics.timeSinceLastBusReset = timeStr;
	}

	// Query and update packet resend requested
	FlyCapture2::CameraStats stats;
	error = m_pCamera->GetStats(&stats);
	if ( error != PGRERROR_OK )
	{
		infoStruct.diagnostics.resendRequested = m_previousPacketResendRequested;
	}
	else
	{
		infoStruct.diagnostics.resendReceived = stats.numResendPacketsRequested;
		int newEvent = stats.numResendPacketsRequested - m_previousPacketResendRequested;
		if(newEvent > 0)
		{
			for (int i = 0; i < newEvent; i++)
			{
				m_pEventStatisticsWindow->AddEvent(NUMBER_OF_PACKET_RESEND_REQUESTED);
			}
		}
		m_previousPacketResendRequested = stats.numResendPacketsRequested;
	}

	//Update packet resend received
	if ( error != PGRERROR_OK )
	{
		infoStruct.diagnostics.resendReceived = m_previousPacketResendReceived;
	}
	else
	{
		infoStruct.diagnostics.resendReceived = stats.numResendPacketsReceived;
		int newEvent = stats.numResendPacketsReceived - m_previousPacketResendReceived;
		if(newEvent > 0)
		{
			for (int i = 0; i < newEvent; i++)
			{
				m_pEventStatisticsWindow->AddEvent(NUMBER_OF_PACKET_RESEND_RECEIVED);
			}
		}
		m_previousPacketResendReceived = stats.numResendPacketsReceived;
	}

	m_pInformationPane->UpdateInformationPane( infoStruct );
}

	void
FlycapWindow::UpdateStatusBar()
{
	char info[512];

	if( GetRunStatus() == true )
	{
		// Get the current mouse position
		int xPos = 0;
		int yPos = 0;
		m_pArea->GetMouseCoordinates( &xPos, &yPos );

		// Set up the frame rate data
		Property prop;
		prop.type = FRAME_RATE;
		Error error = m_pCamera->GetProperty( &prop );

		unsigned int redVal = 0;
		unsigned int greenVal = 0;
		unsigned int blueVal = 0;

		m_pArea->GetCurrentRGB(&redVal, &greenVal, &blueVal);

		unsigned int displayCols, displayRows;
		double magRate;
		m_pArea->GetDisplaySizeAndMagnificationRate( displayCols, displayRows, magRate);

		const unsigned int imageWidth = m_imageWidth;
		const unsigned int imageHeight = m_imageHeight;

		float receivedPercentage = 0.0;
		if (m_receivedDataSize != 0 && m_dataSize != 0)
		{
			receivedPercentage = ((float)m_receivedDataSize/(float)m_dataSize) * 100.0f;
		}

		const float processedFrameRate = m_processedFrameRate.GetFrameRate();

		const float currBandwidth = (m_receivedDataSize * processedFrameRate)/(1024*1024);

		sprintf(
				info,
				"Frame Rate (Proc/Disp/Req): %3.2fHz / %3.2fHz / %3.2fHz | Bandwidth used: %4.1fMB/s | Received data: %3.1fMB/%3.1fMB (%3.1f%%) | Cursor: (%4u, %4u) | RGB: (%3d %3d %3d) | Zoom: %4.1lf%% | Image size / Display size: (%u, %u) / (%u, %u)",
				processedFrameRate,
				m_pArea->GetDisplayedFrameRate(),
				(error == PGRERROR_OK) ? prop.absValue : 0.0,
				currBandwidth,
				(float)m_receivedDataSize/(1024*1024),
				(float)m_dataSize/(1024*1024),
				receivedPercentage,
				xPos >= 0 ? xPos : 0,
				yPos >= 0 ? yPos : 0,
				redVal,
				greenVal,
				blueVal,
				magRate * 100.0,
				imageWidth,
				imageHeight,
				displayCols,
				displayRows );
	}
	else
	{
		sprintf( info, "Camera not started" );
	}

	m_pStatusBarRGB->pop();
	m_pStatusBarRGB->push( info );
}

void FlycapWindow::UpdateHistogramWindow()
{
	if ( m_pHistogramWindow->is_visible() == true )
	{
		m_pHistogramWindow->Update();
	}
}

void FlycapWindow::UpdateEventStatisticsWindow()
{
	if ( m_pEventStatisticsWindow->is_visible() == true )
	{
		m_pEventStatisticsWindow->Update();
	}
}

void FlycapWindow::UpdateScrollbars()
{
	double currX, currY;
	m_pArea->GetImageShift( currX, currY );
	m_pHScrollbar->set_value(1.0 - currX);
	m_pVScrollbar->set_value( currY );
}

	void
FlycapWindow::LoadPGRLogo()
{
	// Attempt to load logo file into a temporary RGB pixbuf
	Glib::RefPtr<Gdk::Pixbuf> tempPixbuf = Gdk::Pixbuf::create_from_inline(
			sizeof(PGRLogo), PGRLogo, false);

	// Create an Image consisting of the pix buf data.
	Image tempImage(
			tempPixbuf->get_height(),
			tempPixbuf->get_width(),
			tempPixbuf->get_rowstride(),
			(unsigned char*)tempPixbuf->get_pixels(),
			tempPixbuf->get_rowstride() * tempPixbuf->get_height(),
			PIXEL_FORMAT_RGB,
			NONE );

	// Byte swap the data, since OpenGL needs data in BGR and not RGB format.
	Image byteSwappedImage;
	tempImage.Convert( PIXEL_FORMAT_BGR, &byteSwappedImage );

	m_imageWidth = byteSwappedImage.GetCols();
	m_imageHeight = byteSwappedImage.GetRows();
	m_bytesPerPixel = byteSwappedImage.GetBitsPerPixel() / 8.0f;
	m_receivedDataSize = 0;
	m_dataSize = 0;

	m_pArea->SetImage(&byteSwappedImage);
}

	void
FlycapWindow::LoadFlyCap2Icon()
{
	m_iconPixBuf = Gdk::Pixbuf::create_from_inline( sizeof(PGRIcon), PGRIcon, false );
}

	void
FlycapWindow::OnMenuDrawCrosshair()
{
	bool show = m_pMenuDrawCrosshair->get_active();
	m_pArea->SetShowCrosshair( show );
}

	void
FlycapWindow::OnMenuChangeCrosshairColor()
{
	Gtk::ColorSelectionDialog colorSlnDlg;

	Gdk::Color currColor = m_pArea->GetCrosshairColor();
	colorSlnDlg.get_colorsel()->set_current_color( currColor );

	int response = colorSlnDlg.run();

	switch( response )
	{
		case Gtk::RESPONSE_OK:
			{
				Gdk::Color newColor = colorSlnDlg.get_colorsel()->get_current_color();
				m_pArea->SetCrosshairColor( newColor );
			}
			break;
		case Gtk::RESPONSE_CANCEL:
		case Gtk::RESPONSE_NONE:
		default:
			break;
	}
}

	void
FlycapWindow::OnMenuShowToolbar()
{
	(m_pMenuShowToolbar->get_active() == true) ? m_pToolbar->show() : m_pToolbar->hide();
}

	void
FlycapWindow::OnMenuShowInfoPane()
{
	bool show = m_pMenuShowInfoPane->get_active();

	if ( show == true )
	{
		m_pInformationPane->set_position( m_prevPanePos );
	}
	else
	{
		// Get the current pane location
		m_prevPanePos = m_pInformationPane->get_position();
		m_pInformationPane->set_position( 0 );
	}
}

	void
FlycapWindow::OnMenuStretchImage()
{
	m_pArea->SetStretchToFit( m_pMenuStretchImage->get_active() );
}

void FlycapWindow::OnMenuFullscreen()
{
	bool fullscreen = m_pMenuFullscreen->get_active();

	if ( fullscreen == true )
	{
		m_pWindow->fullscreen();
		m_pToolbar->hide();
		m_pStatusBarRGB->hide();
		m_prevPanePos = m_pInformationPane->get_position();
		m_pInformationPane->set_position(0);
		m_pMenuStretchImage->set_active(true);
	}
	else
	{
		m_pWindow->unfullscreen();
		m_pToolbar->show();
		m_pStatusBarRGB->show();
		m_pInformationPane->set_position( m_prevPanePos );
		m_pMenuStretchImage->set_active(false);
	}
}

	void
FlycapWindow::OnMenuCPAClicked( ColorProcessingAlgorithm cpa, Gtk::RadioMenuItem* pMenuItem )
{
	if( pMenuItem->get_active() != true )
	{
		return;
	}

	Image::SetDefaultColorProcessing( cpa );
}

void FlycapWindow::OnBusArrival( void* pParam, unsigned int serialNumber )
{
	FlycapWindow* pWin =  static_cast<FlycapWindow*>(pParam);
	Glib::Mutex::Lock queueLock(pWin->m_arrQueueMutex);
	pWin->m_arrQueue.push(serialNumber);
	pWin->m_pBusArrivalEvent->emit();
}

void FlycapWindow::OnBusArrivalHandler()
{
	m_pEventStatisticsWindow->AddEvent(NUMBER_OF_BUS_ARRIVALS);

	unsigned int serialNumber;
	Glib::Mutex::Lock queueLock(m_arrQueueMutex);
	serialNumber = m_arrQueue.front();
	m_arrQueue.pop();
}

void FlycapWindow::OnBusRemoval( void* pParam , unsigned int serialNumber)
{
	FlycapWindow* pWin = static_cast<FlycapWindow*>(pParam);
	Glib::Mutex::Lock queueLock(pWin->m_remQueueMutex);
	pWin->m_remQueue.push(serialNumber);
	pWin->m_pBusRemovalEvent->emit();
}

void FlycapWindow::OnBusRemovalHandler()
{
	m_pEventStatisticsWindow->AddEvent(NUMBER_OF_BUS_REMOVALS);

	unsigned int serialNumber;
	Glib::Mutex::Lock queueLock(m_remQueueMutex);
	serialNumber = m_remQueue.front();
	m_remQueue.pop();
	if( m_camInfo.serialNumber == serialNumber )
	{
		Stop();
		m_pCamera->Disconnect();
	}
}

void FlycapWindow::OnBusReset( void* pParam, unsigned int serialNumber )
{
	FlycapWindow* pWin = static_cast<FlycapWindow*>(pParam);
	pWin->m_pBusResetEvent->emit();
}

void FlycapWindow::OnBusResetHandler()
{
	m_pEventStatisticsWindow->AddEvent(NUMBER_OF_BUS_RESETS);
}

	void
FlycapWindow::OnMenuHelp()
{
	LaunchHelp();
}

	void
FlycapWindow::OnMenuAbout()
{
	Gtk::AboutDialog aboutDlg;

	char timeStamp[512];
	sprintf( timeStamp, "%s %s", __DATE__, __TIME__ );

	Glib::ustring comments( "Image acquisition and camera control application for FlyCapture 2.\nBuilt: " );
	comments += timeStamp;

	aboutDlg.set_program_name( "FlyCap2" );
	aboutDlg.set_comments( comments );
	aboutDlg.set_copyright( "© FLIR Integrated Imaging Solutions, Inc. All Rights Reserved." );

	FC2Version fc2Version;
	Utilities::GetLibraryVersion( &fc2Version );
	char version[128];
	sprintf( version, "%d.%d.%d.%d", fc2Version.major, fc2Version.minor, fc2Version.type, fc2Version.build );

	aboutDlg.set_version( version );

	Glib::ustring ustrLicense;
	ustrLicense.append(
			"The FlyCapture Software Development Kit (the \"Software\") is owned and copyrighted by FLIR Integrated Imaging Solutions, Inc.  All rights are reserved.\n"
			"The Original Purchaser is granted a license to use the Software subject to the following restrictions and limitations.\n"
			"1.	The license is to the Original Purchaser only, and is nontransferable unless you have received written permission of FLIR Integrated Imaging Solutions, Inc.\n"
			"2.	The Original Purchaser may use the Software only with FLIR Integrated Imaging Solutions, Inc. cameras owned by the Original Purchaser, including but not limited to, Flea, Flea2, Firefly2, Firefly MV, Dragonfly, Dragonfly2, Dragonfly Express or Scorpion Camera Modules.\n"
			"3.	The Original Purchaser may make back-up copies of the Software for his or her own use only, subject to the use limitations of this license.\n"
			"4.	Subject to s.5 below, the Original Purchaser may not engage in, nor permit third parties to engage in, any of the following:\n"
			"a)	Providing or disclosing the Software to third parties.\n"
			"b)	Making alterations or copies of any kind of the Software (except as specifically permitted in s.3 above).\n"
			"c)	Attempting to un-assemble, de-compile or reverse engineer the Software in any way.\n"
			"Granting sublicenses, leases or other rights in the Software to others.\n"
			"5.	Original Purchasers who are Original Equipment Manufacturers may make Derivative Products with the Software. Derivative Products are new software products developed, in whole or in part, using the Software and other FLIR Integrated Imaging Solutions, Inc. products.\n"
			"FLIR Integrated Imaging Solutions, Inc. hereby grants a license to Original Equipment Manufacturers to incorporate and distribute the libraries found in the Software with the Derivative Products.\n"
			"The components of any Derivative Product that contain the Software libraries may only be used with FLIR Integrated Imaging Solutions, Inc. products, or images derived from such products.\n"
			"5.1	By the distribution of the Software libraries with Derivative Products, Original Purchasers agree to:\n"
			"a)	not permit further redistribution of the Software libraries by end-user customers;\n"
			"b)	include a valid copyright notice on any Derivative Product; and\n"
			"c)	indemnify, hold harmless, and defend FLIR Integrated Imaging Solutions, Inc. from and against any claims or lawsuits, including attorney's fees, that arise or result from the use or distribution of any Derivative Product.\n"
			"6.	FLIR Integrated Imaging Solutions, Inc. reserves the right to terminate this license if there are any violations of its terms or if there is a default committed by the Original Purchaser.\n"
			"Upon termination, for any reason, all copies of the Software must be immediately returned to FLIR Integrated Imaging Solutions, Inc. and the Original Purchaser shall be liable to FLIR Integrated Imaging Solutions, Inc. for any and all damages suffered as a result of the violation or default.");

	aboutDlg.set_wrap_license( true );
	aboutDlg.set_license( ustrLicense );
	aboutDlg.set_logo( m_iconPixBuf );

	aboutDlg.run();
}

	int
FlycapWindow::ShowErrorMessageDialog( Glib::ustring mainTxt, Glib::ustring secondaryTxt )
{
	Gtk::MessageDialog dialog( mainTxt, false, Gtk::MESSAGE_ERROR, Gtk::BUTTONS_OK );
	dialog.set_secondary_text( secondaryTxt );

	return dialog.run();
}

	int
FlycapWindow::ShowErrorMessageDialog( Glib::ustring mainTxt, Error error, bool detailed )
{
	if ( detailed == true )
	{
		char tempStr[1024];
		sprintf(
				tempStr,
				"Source: %s(%u) Built: %s - %s\n",
				error.GetFilename(),
				error.GetLine(),
				error.GetBuildDate(),
				error.GetDescription() );

		Glib::ustring errorTxt(tempStr);

		Error cause = error.GetCause();
		while( cause.GetType() != PGRERROR_UNDEFINED )
		{
			sprintf(
					tempStr,
					"+-> From: %s(%d) Built: %s - %s\n",
					cause.GetFilename(),
					cause.GetLine(),
					cause.GetBuildDate(),
					cause.GetDescription() );

			errorTxt.append( tempStr );

			cause = cause.GetCause();
		}

		return ShowErrorMessageDialog( mainTxt, errorTxt );
	}
	else
	{
		return ShowErrorMessageDialog( mainTxt, error.GetDescription() );
	}
}

bool FlycapWindow::OnHScroll( Gtk::ScrollType /*type*/, double newValue )
{
	double currX, currY;
	m_pArea->GetImageShift( currX, currY );
	m_pArea->SetImageShift( 1.0 - newValue, currY );
	m_pArea->queue_draw();

	return true;
}

bool FlycapWindow::OnVScroll( Gtk::ScrollType /*type*/, double newValue )
{
	double currX, currY;
	m_pArea->GetImageShift( currX, currY );
	m_pArea->SetImageShift( currX, newValue );
	m_pArea->queue_draw();

	return true;
}

void FlycapWindow::OnImageMoved( double /*newX*/, double /*newY*/ )
{
	UpdateScrollbars();
	UpdateStatusBar();
}
