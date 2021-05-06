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
// $Id: LUTPage.h,v 1.14 2010-10-12 17:45:19 soowei Exp $
//=============================================================================

#ifndef _LUTPAGE_H_
#define _LUTPAGE_H_

#include "BasePage.h"

namespace FlyCapture2
{
	/** Model for the channel combo box. */
	class LUTBankColumns : public Gtk::TreeModelColumnRecord
	{
		public:
			/** Channel name. */
			Gtk::TreeModelColumn<Glib::ustring> m_colBankStr;

			/** Channel value. For multi channel LUT, -1 signifies all channels. */
			Gtk::TreeModelColumn<int> m_colBank;

			LUTBankColumns()
			{
				add( m_colBankStr );
				add( m_colBank );
			}
	};

	/** Model for the channel combo box. */
	class LUTChannelColumns : public Gtk::TreeModelColumnRecord
	{
		public:
			/** Channel name. */
			Gtk::TreeModelColumn<Glib::ustring> m_colChannelStr;

			/** Channel value. For multi channel LUT, -1 signifies all channels. */
			Gtk::TreeModelColumn<int> m_colChannel;

			LUTChannelColumns()
			{
				add( m_colChannelStr );
				add( m_colChannel );
			}
	};

	class LUTPage : public BasePage
	{
		public:
			LUTPage( CameraBase* pCamera, Glib::RefPtr<Gnome::Glade::Xml> refXml );
			~LUTPage();

			void UpdateWidgets();

			void OnFormatChanged();

		protected:
			void GetWidgets();
			void AttachSignals();

		private:

			static const char* sk_curveLUT;
			static const char* sk_inputMin;
			static const char* sk_inputMid;
			static const char* sk_inputMax;
			static const char* sk_outputMin;
			static const char* sk_outputMid;
			static const char* sk_outputMax;
			static const char* sk_resetButton;
			static const char* sk_bankCombo;
			static const char* sk_channelCombo;
			static const char* sk_loadFile;
			static const char* sk_saveFile;
			static const char* sk_loadCamera;
			static const char* sk_setCamera;
			static const char* sk_enable;
			static const char* sk_linearRadio;
			static const char* sk_splineRadio;
			static const char* sk_freeRadio;

			Gtk::Curve* m_pCurve;

			Gtk::Button* m_pSaveFile;
			Gtk::Button* m_pLoadFile;
			Gtk::Button* m_pSetCamera;
			Gtk::Button* m_pLoadCamera;
			Gtk::Button* m_pReset;

			Gtk::ComboBox* m_pBank;

			Gtk::ComboBox* m_pChannel;
			Gtk::CheckButton* m_pEnable;

			Gtk::RadioButton* m_pSpline;
			Gtk::RadioButton* m_pLinear;
			Gtk::RadioButton* m_pFree;

			Gtk::Label* m_pInputMin;
			Gtk::Label* m_pInputMid;
			Gtk::Label* m_pInputMax;
			Gtk::Label* m_pOutputMin;
			Gtk::Label* m_pOutputMid;
			Gtk::Label* m_pOutputMax;

			LUTBankColumns m_channelBanks;
			Glib::RefPtr<Gtk::ListStore> m_refListStoreBanks;

			LUTChannelColumns m_channelColumns;
			Glib::RefPtr<Gtk::ListStore> m_refListStoreChannels;

			LUTPage();
			LUTPage( const LUTPage& );
			LUTPage& operator=( const LUTPage& );

			void OnReset();
			void OnSaveToFile();
			void OnLoadFromFile();
			void OnLoadFromCamera();
			void OnSetToCamera();
			void OnStyleChange();
			void OnBankChange();
			void OnChannelChange();
			void OnToggleEnable();
			void OnCurveStyleChanged();

			void DisableWidgets();
			void EnableWidgets();

			/**
			 * Get the currently selected channel. See LUTChannelColumns for
			 * more details on the return value.
			 *
			 * @return Currently selected channel.
			 */
			int GetActiveChannelComboBox();

			/**
			 * Add the specified channel to the combo box.
			 *
			 * @param description Channel description.
			 * @param channel Channel value.
			 */
			void AddToChannelComboBox( Glib::ustring description, int channel );

			/**
			 * Populate the channel combo box with the specified number of
			 * channels.
			 *
			 * @param numChannels Number of channels to populate with.
			 */
			void PopulateChannelComboBox( unsigned int numChannels );

			/**
			 * Get the currently selected bank.
			 *
			 * @return Currently selected bank.
			 */
			int GetActiveBankComboBox();

			/**
			 * Populate the bank combo box with the specified number of
			 * banks.
			 *
			 * @param numBanks Number of banks to populate with.
			 */
			void PopulateBankComboBox( unsigned int numBanks );

			/**
			 * Add file filters when opening a file chooser dialog.
			 *
			 * @param dialog Dialog to add file filters to.
			 */
			void AddFileFilters( Gtk::FileChooserDialog& dialog );
	};
}

#endif // _LUTPAGE_H_
