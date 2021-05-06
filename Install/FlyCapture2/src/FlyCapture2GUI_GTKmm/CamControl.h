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
// $Id: CamControl.h,v 1.28 2010/12/02 18:14:47 hirokim Exp $
//=============================================================================

#ifndef CAMCONTROL_H_INCLUDED
#define CAMCONTROL_H_INCLUDED

#include <list>
#include <stdio.h>
#include <string.h>

namespace FlyCapture2
{
	// Forward declarations
	class BasePage;
	class Format7Page;
	class DCAMFormatsPage;
	class CamSettingsPage;
	class CamInfoPage;
	class RegisterPage;
	class GPIOPage;
	class AdvCameraSettingsPage;
	class HDRPage;
	class LUTPage;
	class FrameBufferPage;
	class DataFlashPage;
	class SystemInfoPage;
	class PhyRegistersPage;
	class BusTopologyPage;
	class MessageLoggingPage;
	class DiagnosticsPage;
	class HelpSupportPage;
	class LadybugSettingsPage;

	class CamControl
	{
		public:
			CamControl();
			~CamControl();

			bool Initialize();

			void Connect( CameraBase* pCamera );
			void Disconnect();

			void Show(bool isModal = false);
			void Hide();
			bool IsVisible ();
			void SetTitle( const char *pTitle);

		protected:

		private:
			static const char* sk_camControlWindow;

			Gtk::Main* m_pKit;

			Glib::RefPtr<Gnome::Glade::Xml> m_refXml;
			Gtk::Window* m_pWindow;

			// CamControl notebook
			Gtk::Notebook* m_pNotebook;

			int m_xPos;
			int m_yPos;

			bool m_bFirst;

			Glib::RefPtr<Gdk::Pixbuf> m_iconPixBuf;

			bool m_run;

			CameraBase* m_pCamera;
			bool m_connected;

			// List to hold all the page objects
			std::list<BasePage*> m_listPages;

			Format7Page* m_pFormat7Page;
			DCAMFormatsPage* m_pDcamFormatsPage;
			CamSettingsPage* m_pCamSettingsPage;
			CamInfoPage* m_pCamInfoPage;
			RegisterPage* m_pRegisterPage;
			GPIOPage* m_pGpioPage;
			AdvCameraSettingsPage* m_pAdvCamSettingsPage;
			HDRPage* m_pHdrPage;
			LUTPage* m_pLutPage;
			FrameBufferPage* m_pFrameBufferPage;
			DataFlashPage* m_pDataFlashPage;
			SystemInfoPage* m_pSystemInfoPage;
			PhyRegistersPage* m_pPhyRegistersPage;
			BusTopologyPage* m_pBusTopologyPage;
			HelpSupportPage* m_pHelpPage;
			LadybugSettingsPage* m_pLadybugSettingsPage;

			void DeleteAllPages();
			void InitializeAllPages();
			void UpdateAllPages();
			void SetCameraAllPages( CameraBase* pCamera );
			void SetCameraInfoAllPages( CameraInfo camInfo );
			void SetConnectedAllPages( bool bConnected );

			bool OnDestroy( GdkEventAny* event );
			bool OnExposeEvent( GdkEventExpose* event );

			void LoadPGRIcon();

			void OnFormat7Applied();
			void OnFormatChanged();
			void OnRestoreFromMemoryChannel();
			void OnSwitchPage( GtkNotebookPage* /*page*/, guint page_num );
	};
}

#endif // CAMCONTROL_H_INCLUDED
