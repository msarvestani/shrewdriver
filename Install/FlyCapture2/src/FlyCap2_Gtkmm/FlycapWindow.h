//=============================================================================
// Copyright � 2017 FLIR Integrated Imaging Solutions, Inc. All Rights Reserved.
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
// FlycapWindow.h,v 1.59 2010/01/14 00:29:51 soowei Exp
//=============================================================================

#ifndef PGR_FC2_FLYCAPWINDOW_H
#define PGR_FC2_FLYCAPWINDOW_H

#include <iostream>
#include <queue>

#include "FlyCapture2.h"
#include "FlyCapture2GUI.h"

#include "FrameRateCounter.h"
#include "ImageDrawingArea.h"
#include "InformationPane.h"
#include "HistogramWindow.h"
#include "EventStatisticsWindow.h"

/**
 * This class represents a window where images can be displayed. It also
 * contains a grab loop and various other features such as image saving.
 */
class FlycapWindow
{
	public:
		/** Constructor. */
		FlycapWindow();

		/** Destructor. */
		~FlycapWindow();

		/**
		 * Perform initialization and start capturing from the camera with the
		 * specified PGRGuid.
		 *
		 * @param guid
		 *
		 * @return Whether the function was successful.
		 */
		bool Run( PGRGuid guid );

		/**
		 * Perform cleanup upon exit.
		 *
		 * @return Whether the cleanup was successful.
		 */
		bool Cleanup();

	protected:

	private:
		/** Number of windows that are active (1 per camera). */
		static int m_activeWindows;

		/** Glade XML object. */
		Glib::RefPtr<Gnome::Glade::Xml> m_refXml;

		/** Main window. */
		Gtk::Window* m_pWindow;

		/** Menu bar. */
		Gtk::MenuBar* m_pMenubar;

		/** Tool bar. */
		Gtk::Toolbar* m_pToolbar;

		Gtk::MenuItem* m_pMenuNewCamera;
		Gtk::MenuItem* m_pMenuStart;
		Gtk::CheckMenuItem* m_pMenuPause;
		Gtk::MenuItem* m_pMenuStop;
		Gtk::ImageMenuItem* m_pMenuSaveAs;
		Gtk::ImageMenuItem* m_pMenuQuit;

		Gtk::CheckMenuItem* m_pMenuDrawImage;
		Gtk::CheckMenuItem* m_pMenuDrawCrosshair;
		Gtk::MenuItem* m_pMenuChangeCrosshairColor;
		Gtk::CheckMenuItem* m_pMenuShowToolbar;
		Gtk::CheckMenuItem* m_pMenuShowInfoPane;
		Gtk::CheckMenuItem* m_pMenuStretchImage;
		Gtk::CheckMenuItem* m_pMenuFullscreen;

		Gtk::RadioMenuItem* m_pMenuCPA_None;
		Gtk::RadioMenuItem* m_pMenuCPA_NNF;
		Gtk::RadioMenuItem* m_pMenuCPA_HQ_Linear;
		Gtk::RadioMenuItem* m_pMenuCPA_Edge_Sensing;
		Gtk::RadioMenuItem* m_pMenuCPA_DirectionalFilter;
		Gtk::RadioMenuItem* m_pMenuCPA_Rigorous;
		Gtk::RadioMenuItem* m_pMenuCPA_IPP;

		Gtk::ImageMenuItem* m_pMenuHelp;
		Gtk::ImageMenuItem* m_pMenuAbout;

		Gtk::ToolButton* m_pNewCameraButton;
		Gtk::ToolButton* m_pStartButton;
		Gtk::ToggleToolButton* m_pPauseButton;
		Gtk::ToolButton* m_pStopButton;
		Gtk::ToolButton* m_pSaveImageButton;
		Gtk::ToolButton* m_pCamCtlButton;
		Gtk::ToolButton* m_pHistogramButton;
		Gtk::ToolButton* m_pEventStatisticsButton;

		Gtk::VScrollbar* m_pVScrollbar;
		Gtk::HScrollbar* m_pHScrollbar;

		sigc::connection m_menuPauseConnection;
		sigc::connection m_toolbarPauseConnection;

		/** The scrolled window that holds the drawing area. */
		Gtk::ScrolledWindow* m_pScrolledWindow;

		/** Status bar. */
		Gtk::Statusbar* m_pStatusBarRGB;

		/** Pane that holds the scrolled window and info pane. */
		InformationPane* m_pInformationPane;

		/** Dispatcher for grab loop to notify main loop. */
		Glib::Dispatcher* m_pNewImageEvent;

		/** Dispatcher for bus arrivals to notify the main loop. */
		Glib::Dispatcher* m_pBusArrivalEvent;

		/** Dispatcher for bus removals to notify the main loop. */
		Glib::Dispatcher* m_pBusRemovalEvent;

		/** Dispatcher for bus resets to notify the main loop. */
		Glib::Dispatcher* m_pBusResetEvent;

		/** Queue that will store serial numbers of arrival cams. */
		std::queue<unsigned int> m_arrQueue;

		/** Mutex to protect access to the arrQueue. */
		Glib::Mutex m_arrQueueMutex;

		/** Queue that will store serial numbers of arrival cams. */
		std::queue<unsigned int> m_remQueue;

		/** Mutex to protect access to the remQueue. */
		Glib::Mutex m_remQueueMutex;

		/** Custom drawing area. */
		ImageDrawingArea* m_pArea;

		/** Histogram window. */
		HistogramWindow* m_pHistogramWindow;

		/** Event statistics window. */
		EventStatisticsWindow* m_pEventStatisticsWindow;

		/** Bus manager. Used for registering and unregistering callbacks.*/
		BusManager m_busMgr;

		/** Camera arrival callback handle. */
		CallbackHandle m_cbArrivalHandle;

		/** Camera removal callback handle. */
		CallbackHandle m_cbRemovalHandle;

		/** Bus reset callback handle. */
		CallbackHandle m_cbResetHandle;

		/** Camera object. */
		CameraBase* m_pCamera;

		/** Camera information for the camera. */
		CameraInfo m_camInfo;

		/** Camera control dialog for the camera. */
		CameraControlDlg m_camCtlDlg;

		/** The raw image returned from the camera. */
		Image m_rawImage;

		/** The temporary image object. */
		Image m_tempImage;

		/** Converted image used for display. */
		Image m_convertedImage;

		/** Image statistics for the current image. */
		ImageStatistics m_imageStats;

		/** Mutex to protect access to the raw image. */
		Glib::Mutex m_rawImageMutex;

		/** Image width. */
		unsigned int m_imageWidth;

		/** Image height. */
		unsigned int m_imageHeight;

		/** Received data size. */
		unsigned int m_receivedDataSize;

		/** Data size. */
		unsigned int m_dataSize;

		/** Bytes per pixel. */
		float m_bytesPerPixel;

		/** PGR icon pixbuf. */
		Glib::RefPtr<Gdk::Pixbuf> m_iconPixBuf;

		/** Whether the grab thread should keep running. */
		bool m_run;

		/** Whether color-processing menu is enabled. */
		bool m_menuEnabled;

		/** Mutex to protect access to the thread run flag. */
		Glib::Mutex m_runMutex;

		/** Pointer to the thread handle for the grab loop. */
		Glib::Thread* m_pGrabLoop;

		/** Processed frame rate counter. */
		FrameRateCounter m_processedFrameRate;

		/** Position of the splitter between information pane and main window. */
		int m_prevPanePos;

		/** Mutex to protect access to the emitted number. */
		Glib::Mutex m_emitMutex;

		/** Last folder location that an image was saved to. */
		std::string m_saveImageLocation;

		/** Last file format that was used to save an image. */
		FlyCapture2::ImageFileFormat m_saveImageFormat;

		/** Previous skipped image count. */
		unsigned int m_previousSkippedImageCount;

		/** Previous link recovery count. */
		unsigned int m_previousLinkRecoveryCount;

		/** Previous transmit failure count. */
		unsigned int m_previousTransmitFailureCount;

		/**
		 * Number of emissions. An emission happens when an image is ready to be
		 * drawn to the screen.
		 */
		int m_numEmitted;

		/**
		 * Helper function that shows an error message dialog with the specified
		 * error.
		 *
		 * @param mainTxt Main text to display.
		 * @param secondaryTxt Secondary text to display
		 *
		 * @return The response from the dialog.
		 */
		static int ShowErrorMessageDialog( Glib::ustring mainTxt, Glib::ustring secondaryTxt );

		/**
		 * Helper function that shows an error message dialog with the specified
		 * error.
		 *
		 * @param mainTxt Main text to display.
		 * @param error Error with description to be used as secondary text.
		 * @param detailed Whether to display a detailed error trace.
		 *
		 * @return The response from the dialog.
		 */
		static int ShowErrorMessageDialog( Glib::ustring mainTxt, Error error, bool detailed = false );

		/**
		 * Bus arrival handler that is passed to BusManager::RegisterCallback().
		 * This simply emits a signal that calls the real handler.
		 *
		 * @param pParam The parameter passed to the BusManager::RegisterCallback().
		 */
		static void OnBusArrival( void* pParam, unsigned int serialNumber );

		/** Actual bus arrival handler. */
		void OnBusArrivalHandler();

		/**
		 * Bus removal handler that is passed to BusManager::RegisterCallback().
		 * This simply emits a signal that calls the real handler.
		 *
		 * @param pParam The parameter passed to the BusManager::RegisterCallback().
		 */
		static void OnBusRemoval( void* pParam, unsigned int serialNumber );

		/** Actual bus removal handler. */
		void OnBusRemovalHandler();

		/**
		 * Bus reset handler that is passed to BusManager::RegisterCallback().
		 * This simply emits a signal that calls the real handler.
		 *
		 * @param pParam The parameter passed to the BusManager::RegisterCallback().
		 */
		static void OnBusReset( void* pParam, unsigned int serialNumber );

		/** Actual bus removal handler. */
		void OnBusResetHandler();

		/**
		 * Load widgets, attach signals and perform other initialization.
		 *
		 * @return Whether the initialization was successful.
		 */
		bool Initialize();

		/** Get widgets for the window. */
		void GetWidgets();

		/** Attach signals to widgets. */
		void AttachSignals();

		bool OnDestroy( GdkEventAny* event );
		void OnMenuSaveAs();
		void OnMenuQuit();
		void OnMenuDrawCrosshair();
		void OnMenuChangeCrosshairColor();
		void OnMenuShowToolbar();
		void OnMenuShowInfoPane();
		void OnMenuStretchImage();
		void OnMenuFullscreen();
		void OnMenuCPAClicked( ColorProcessingAlgorithm cpa, Gtk::RadioMenuItem* pMenuItem );
		void OnMenuHelp();
		void OnMenuAbout();
		void OnMenuPaused();
		void OnToolbarNewCamera();
		void OnToolbarStart();
		void OnToolbarPaused();
		void OnToolbarStop();
		void OnToolbarCameraControl();
		void OnToolbarHistogram();
		void OnToolbarEventStatistics();
		void OnImageCaptured();
		bool OnMouseScroll( GdkEventScroll* event );

		bool OnHScroll( Gtk::ScrollType type, double newValue );
		bool OnVScroll( Gtk::ScrollType type, double newValue );

		void OnImageMoved( double newX, double newY );

		void UpdateColorProcessingMenu();

		void UpdateInformationPane();
		void UpdateStatusBar();
		void UpdateHistogramWindow();
		void UpdateEventStatisticsWindow();
		void UpdateScrollbars();

		/** Load the PGR logo. It is shown when the camera is not streaming. */
		void LoadPGRLogo();

		/** Load the PGR icon. */
		void LoadFlyCap2Icon();

		/**
		 * Start running with the specified PGRGuid.
		 *
		 * @return Whether the function succeeded.
		 */
		bool Start( PGRGuid guid );

		/**
		 * Stop image capture.
		 *
		 * @return Whether the function succeeded.
		 */
		bool Stop();

		/** Register all relevant callbacks with the library. */
		void RegisterCallbacks();

		/** Unregister all relevant callbacks with the library. */
		void UnregisterCallbacks();

		/** Start grab thread. */
		void LaunchGrabThread();

		/** Stop grab thread. */
		void KillGrabThread();

		/** Set the run status. */
		void SetRunStatus( bool runStatus );

		/** Get the run status. */
		bool GetRunStatus();

		/** Enable or disable embedded image information timestamp. */
		void SetTimestamping( bool onOff );

		/** Force camera to the PGR Y16 endianness. */
		void ForcePGRY16Mode();

		/**
		 * Parse the time register in hours, minutes and seconds.
		 *
		 * @param timeRegVal Value of the time register.
		 * @param hours Parsed hours.
		 * @param mins Parsed minutes.
		 * @param seconds Parsed seconds.
		 */
		static void ParseTimeRegister(
				unsigned int timeRegVal,
				unsigned int& hours,
				unsigned int& mins,
				unsigned int& seconds );

		/**
		 * Grab thread function.
		 */
		void GrabLoop();

		/**
		 * Helper function to print grab loop errors out to console. Appends
		 * the current time to the front of the output.
		 *
		 * @param fc2Error Error to be printed.
		 */
		void PrintGrabLoopError( Error fc2Error );

		/**
		 * Helper function to determine whether pixel format was raw
		 *
		 * @param image FlyCapture2 Image.
		 */
		bool IsRAWPixelFormat(Image &image);

		/**
		 * Helper function to enable/disable color-processing menu
		 *
		 * @param enable Boolean to indicate whether to enable or disable menu.
		 */
		void ToggleColorMenu(bool enable);

		/**
		 * Reset Pause toolbar button and menu item
		 *
		 *@param enable Boolean to indicate whether to enable or disable menu.
		 */
		void ResetPauseButtons(bool sensitivity);
		int m_previousPacketResendRequested;
		int m_previousPacketResendReceived;
		bool m_cameraPaused;
};

#endif // PGR_FC2_FLYCAPWINDOW_H
